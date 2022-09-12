import math
import os
from collections import namedtuple, defaultdict

import pandas as pd
import requests

from api_data import ApiDataInterface, Tables, Table
from web_data import ColumnNames, RowDataGetter, DataDescription, Links, WebDataGenerator

PersonType = namedtuple('PersonType', ['name', 'category'])
InjuryType = namedtuple('InjuryType', ['name', 'category', 'number'])

BASE_URL = 'https://crashviewer.nhtsa.dot.gov/CrashAPI'
DATA_API = f'{BASE_URL}/FARSData'

FARS_TABLES = Tables(
    key_columns=['CASEYEAR', 'STATE', 'ST_CASE'],
    crash=Table(name='Accident', columns=['LATITUDE', 'LONGITUD', 'FATALS']),
    person=Table(name='Person', columns=['PER_TYP', 'PER_TYPNAME', 'INJ_SEV', 'INJ_SEVNAME', 'AGE']),
    vehicle=Table(name='Vehicle', columns=[]),
)

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
    def item_id(self, row):
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


class FarsApiDataInterface(ApiDataInterface):
    def __init__(self):
        super(FarsApiDataInterface, self).__init__(entity='fars', tables=FARS_TABLES)
        self.years = range(2020, 2021)

    def download_data(self, refresh=False):
        if not os.path.exists(self.data_dir()):
            os.makedirs(self.data_dir())
        for table in self.tables.get_tables():
            for year in self.years:
                output_path = self.downloaded_data_file(table.name, year)
                if not refresh and os.path.exists(output_path):
                    continue
                params = {'dataset': table.name, 'State': '*', 'FromYear': year, 'ToYear': year}
                response = requests.get(DATA_API, params)
                response.encoding = 'utf-8-sig'
                with open(output_path, 'w') as outfile:
                    outfile.write(response.text)

    def convert_to_df(self):
        for table in self.tables.get_tables():
            for year in self.years:
                df = pd.read_csv(self.downloaded_data_file(table.name, year))
                df.to_pickle(self.unfiltered_data_file(table.name, year))

    def downloaded_data_file(self, dataset_name, year):
        return f'{self.data_dir()}/{dataset_name.lower()}-{year}.csv'

    def merged_data_file(self, year):
        return f'{self.data_dir()}/df-{year}.pkl'

    def convert_data_types(self, df, dataset: Table = None):
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')


if __name__ == '__main__':
    data_interface = FarsApiDataInterface()
    data_interface.process_data(year=2020)
    df = data_interface.read_data()

    print('Generating web data...')
    web_data_generator = WebDataGenerator(row_data_getter=FarsRowDataGetter(column_names=COLUMN_NAMES),
                                          column_names=COLUMN_NAMES,
                                          data_description=FARS_DATA_DESCRIPTION)
    web_data_generator.iterate_and_save(df, latlong_interval=2)
