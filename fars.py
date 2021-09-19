import math
from collections import namedtuple, defaultdict

from web_data import ColumnNames, RowDataGetter, DataDescription, Links

PersonType = namedtuple('PersonType', ['name', 'category'])
InjuryType = namedtuple('InjuryType', ['name', 'category', 'number'])

FARS_DATA_DESCRIPTION = DataDescription(
    title='Traffic fatalities in the United States',
    source='United States National Highway Traffic Safety Administration, '
           '<a href="https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars">Fatality Analysis '
           'Reporting System</a>. Tracks crashes with fatalities only. 2020 data will be released in December 2021.',
    state='fars',
    record_links=Links(id_splitter='-',
                       crash_format='https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCaseDetails'
                                    '?caseYear={}&state={}&stateCase={}&format=xml')
)

COLUMN_NAMES = ColumnNames(latitude='LATITUDE', longitude='LONGITUD', year='CASEYEAR')

PER_TYPE = {
    1: PersonType('Driver', 'car'),
    2: PersonType('Passenger', 'car'),
    3: PersonType('Occupant, motor vehicle not in-transport', 'car'),
    4: PersonType('Occupant, non-motor vehicle transport device', 'car'),
    5: PersonType('Pedestrian', 'ped'),
    6: PersonType('Bicyclist', 'bike'),
    7: PersonType('Cyclist (other than bicyclist)', 'bike'),
    8: PersonType('Person on personal conveyances', 'ped'),
    9: PersonType('Unknown (occupant of motor vehicle in-transport)', 'other'),
    10: PersonType('Person in building', 'other'),
    19: PersonType('Unknown (non-motorist)', 'other'),
}
UNKNOWN_PER_TYPE = PersonType('Unknown', 'other')
PER_TYPE_PRIORITIES = [  # increasing order
    'car', 'other', 'bike', 'ped',
]
INJURY_TYPE = {
    0: InjuryType('No apparent injury', 'others', 0),
    1: InjuryType('Possible injury', 'injuries', 1),
    2: InjuryType('Suspected minor injury', 'injuries', 2),
    3: InjuryType('Suspected serious injury', 'injuries', 3),
    4: InjuryType('Fatal injury', 'fatalities', 4),
    5: InjuryType('Injury, severity unknown', 'injuries', 5),
    6: InjuryType('Died prior to crash', 'others', 6),
}
UNKNOWN_INJURY_TYPE = InjuryType('Unknown', 'others', -1)


def invert_dict(orig, key):
    inv = {}
    for k, v in orig.items():
        inv.setdefault(v._asdict()[key], []).append(k)
    return inv


INJURY_TYPE_GROUPS = invert_dict(INJURY_TYPE, 'category')


def get_person_type(person):
    return PER_TYPE.get(person['PER_TYP'], UNKNOWN_PER_TYPE)


def get_injury_type(person):
    return INJURY_TYPE.get(person['INJ_SEV'], UNKNOWN_INJURY_TYPE)


def get_category(people):
    max_category = -1
    for p in people:
        if not get_injury_type(p).category == 'fatalities':
            continue
        category = PER_TYPE_PRIORITIES.index(get_person_type(p).category)
        if category > max_category:
            max_category = category
    return PER_TYPE_PRIORITIES[max_category] if max_category > -1 else 'other'


def get_num_fatalities(people):
    num_fatalities = 0
    for p in people:
        if int(p['INJ_SEV']) == 4:
            num_fatalities += 1
    return num_fatalities


class FarsRowDataGetter(RowDataGetter):
    @staticmethod
    def item_id(row):
        return f'{row["CASEYEAR"]}-{row["STATE"]}-{row["ST_CASE"]}'

    @staticmethod
    def category(row):
        return get_category(row['Person'])

    @staticmethod
    def num_fatalities(row):
        return int(row['FATALS']) if not math.isnan(row['FATALS']) else get_num_fatalities(row['Person'])

    @staticmethod
    def num_vehicles(row):
        return row['Vehicle']

    @staticmethod
    def injuries(row):
        injuries = defaultdict(list)
        for p in row['Person']:
            injury_type = get_injury_type(p)
            person_type = get_person_type(p).name
            info = {'person': person_type, 'age': p['AGE'] if 'AGE' in p and p['AGE'] < 900 else 'unknown'}
            if len(INJURY_TYPE_GROUPS[injury_type.category]) > 1:
                info['severity'] = injury_type.name
            injuries[injury_type.category].append(info)
        return injuries
