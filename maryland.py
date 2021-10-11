import math
from collections import defaultdict
from datetime import datetime

import pandas as pd

from api_data import ApiDataInterface, Table, Tables
from constants import InjuryType, PersonType, UNKNOWN, CrashCategory
from web_data import ColumnNames, WebDataGenerator, RowDataGetter, DataDescription, Links

DATE_OF_BIRTH_COLUMN = 'DATE_OF_BIRTH'
INJURY_SEVERITY_COLUMN = 'INJ_SEVER_CODE'
PERSON_TYPE_COLUMN = 'PERSON_TYPE'

WEB_BASE_DIR = 'web'
DATA_BASE_DIR = 'data/maryland'

HARM = {
    'Pedestrian': CrashCategory.PEDESTRIAN,
    'Bicycle': CrashCategory.BICYCLE,
}

MARYLAND_TABLES = Tables(
    key_columns=['REPORT_NO'],
    crash=Table(name='Crash',
                columns=['REPORT_TYPE', 'HARM_EVENT_DESC1', 'HARM_EVENT_DESC2', 'LATITUDE', 'LONGITUDE',
                         'YEAR', 'ACC_DATE']),
    person=Table(name='Person',
                 columns=[PERSON_TYPE_COLUMN, INJURY_SEVERITY_COLUMN, DATE_OF_BIRTH_COLUMN]),
    vehicle=Table(name='Vehicle', columns=[]),
)

COLUMN_NAMES = ColumnNames(latitude='LATITUDE', longitude='LONGITUDE', year='YEAR', id='REPORT_NO')

MARYLAND_DATA_DESCRIPTION = DataDescription(
    title='Crashes with Injuries or Fatalities in Maryland',
    source='Maryland State Police <a href="https://opendata.maryland.gov/Public-Safety/Maryland-Statewide-Vehicle'
           '-Crashes/65du-s3qu">Maryland Statewide Vehicle Crashes</a>. Data is updated quarterly.',
    state='maryland',
    record_links=Links(crash_format='https://opendata.maryland.gov/resource/65du-s3qu.xml?report_no={}',
                       person_format='https://opendata.maryland.gov/resource/py4c-dicf.xml?report_no={}',
                       vehicle_format='https://opendata.maryland.gov/resource/mhft-5t5y.xml?report_no={}')
)

INJURY_CODE_TO_INJURY = {
    1: InjuryType.NO_INJURY,  # No Injury
    2: InjuryType.INJURY,  # Non-incapacitating Injury
    3: InjuryType.INJURY,  # Possible Incapacitating Injury
    4: InjuryType.INJURY,  # Incapacitating/Disabled Injury
    5: InjuryType.FATALITY,  # Fatal Injury
}

PERSON_TYPE_CODE_TO_PERSON = {
    'D': PersonType.DRIVER,
    'O': PersonType.OCCUPANT,
    'P': PersonType.PEDESTRIAN,
}


def injury_type(person):
    return INJURY_CODE_TO_INJURY.get(person[INJURY_SEVERITY_COLUMN])


def person_type(person):
    return PERSON_TYPE_CODE_TO_PERSON.get(person[PERSON_TYPE_COLUMN])


class MarylandApiDataInterface(ApiDataInterface):
    def __init__(self):
        super(MarylandApiDataInterface, self).__init__(entity='maryland', tables=MARYLAND_TABLES)

    def convert_to_df(self):
        datasets_to_filenames = {
            self.tables.crash.name: 'Maryland_Statewide_Vehicle_Crashes.csv',
            self.tables.person.name: 'Maryland_Statewide_Vehicle_Crashes_-_Person_Details__Anonymized_.csv',
            self.tables.vehicle.name: 'Maryland_Statewide_Vehicle_Crashes_-_Vehicle_Details.csv',
        }

        for table, filename in datasets_to_filenames.items():
            df = pd.read_csv(f'{self.data_dir()}/{filename}')
            df.to_pickle(self.unfiltered_data_file(table, year='all'))

    def filter_rows(self, df, dataset: Table = None):
        if dataset.name == 'Crash':
            return df.loc[(df['REPORT_TYPE'] == 'Fatal Crash') | (df['REPORT_TYPE'] == 'Injury Crash')]
        return df

    def convert_data_types(self, df, dataset: Table = None):
        if dataset.name == 'Crash':
            df['ACC_DATE'] = df['ACC_DATE'].astype(str)
        if dataset.name == 'Person':
            df[DATE_OF_BIRTH_COLUMN] = df[DATE_OF_BIRTH_COLUMN].astype(str)


def safe_int(maybe_nan):
    if not maybe_nan or math.isnan(maybe_nan):
        return 0
    return int(maybe_nan)


def parse_date(date_str):
    if not date_str or date_str == 'nan' or date_str == '1/1/1900':
        return UNKNOWN
    for suffix in ['.0', ' 00:00:00', ' ']:
        if date_str.endswith(suffix):
            date_str = date_str[:-len(suffix)]
    if date_str.isnumeric():
        return datetime.strptime(date_str, '%Y%m%d')
    else:
        return datetime.strptime(date_str, '%d-%b-%y')


def age(birth_date_str: str, crash_date_str: str):
    birth_date = parse_date(birth_date_str)
    crash_date = parse_date(crash_date_str)

    if birth_date == UNKNOWN or crash_date == UNKNOWN:
        return UNKNOWN

    return crash_date.year - birth_date.year - ((crash_date.month, birth_date.day) < (crash_date.month, birth_date.day))


class MarylandRowDataGetter(RowDataGetter):
    @staticmethod
    def category(row):
        desc = row['HARM_EVENT_DESC1']
        if desc in HARM:
            return HARM[desc].value
        injuries = map(lambda p: (injury_type(p), person_type(p)), row['Person'])
        max_injury_person = max(injuries, key=lambda i: (i[0].value.severity, i[1].value.vulnerability))
        return max_injury_person[1].value.category.value

    @staticmethod
    def num_vehicles(row):
        return safe_int(row['Vehicle'])

    @staticmethod
    def num_fatalities(row):
        num_fatalities = 0
        for p in row['Person']:
            if injury_type(p) == InjuryType.FATALITY:
                num_fatalities += 1
        return num_fatalities

    @staticmethod
    def injuries(row):
        injuries = defaultdict(list)
        for p in row['Person']:
            info = {
                'person': person_type(p).value.description,
                'age': age(p[DATE_OF_BIRTH_COLUMN], row['ACC_DATE']),
            }
            injuries[injury_type(p).value.category.value].append(info)
        return injuries


if __name__ == '__main__':
    data_interface = MarylandApiDataInterface()
    # data_interface.process_data(year='all')
    df = data_interface.read_data()

    print('Generating web data...')
    web_data_generator = WebDataGenerator(row_data_getter=MarylandRowDataGetter(column_names=COLUMN_NAMES),
                                          column_names=COLUMN_NAMES,
                                          data_description=MARYLAND_DATA_DESCRIPTION)
    web_data_generator.iterate_and_save(df, latlong_interval=2)
