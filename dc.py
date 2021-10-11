import math
from collections import defaultdict

import pandas as pd

from api_data import ApiDataInterface, Table, Tables
from constants import PersonType, InjuryType, CrashCategory
from web_data import RowDataGetter, WebDataGenerator, DataDescription, Links, ColumnNames

INJURY_PREFIXES = ['MAJORINJURIES', 'MINORINJURIES', 'UNKNOWNINJURIES', 'FATAL']
PERSON_TYPE_SUFFIXES = ['_BICYCLIST', '_DRIVER', '_PEDESTRIAN', 'PASSENGER']

INJURY_FATALITY_COLUMNS = [i + p for i in INJURY_PREFIXES for p in PERSON_TYPE_SUFFIXES]
FATALITY_COLUMNS = ['FATAL' + p for p in PERSON_TYPE_SUFFIXES]

DC_TABLES = Tables(
    key_columns=['CRIMEID'],
    crash=Table(name='Crash', columns=['LATITUDE', 'LONGITUDE', 'YEAR', 'TOTAL_VEHICLES'] + INJURY_FATALITY_COLUMNS,
                url='https://opendata.arcgis.com/api/v3/datasets/70392a096a8e431381f1f692aaa06afd_24/downloads/data'
                    '?format=csv&spatialRefId=4326'),
    detail=Table(name='Detail', columns=['PERSONTYPE', 'AGE', 'FATAL', 'MAJORINJURY', 'MINORINJURY'],
                 url='https://opendata.arcgis.com/api/v3/datasets/70248b73c20f46b0a5ee895fc91d6222_25/downloads/data'
                     '?format=csv&spatialRefId=4326'),
)

DC_DATA_DESCRIPTION = DataDescription(
    title='Crashes with Injuries or Fatalities in the District of Columbia',
    source='District Department of Transportation <a '
           'href="https://opendata.dc.gov/datasets/DCGIS::crashes-in-dc/about">Crashes in DC</a>. Data is updated '
           'daily.',
    state='dc',
    record_links=Links(
        crash_format='https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Public_Safety_WebMercator/MapServer'
                     '/24/query?where=CRIMEID={}&outFields=*&outSR=4326&f=pjson')
)

COLUMN_NAMES = ColumnNames(id='CRIMEID')

PERSON_TYPE_COLUMN = 'PERSONTYPE'

PERSON_TYPE_TO_PERSON = {
    'Bicyclist': PersonType.BICYCLIST,
    'Driver': PersonType.DRIVER,
    'Electric M': PersonType.OTHER,
    'Occupant o': PersonType.OCCUPANT,
    'Passenger': PersonType.OCCUPANT,
    'Pedestrian': PersonType.PEDESTRIAN,
    'Streetcar': PersonType.OTHER,
    'Unknown': PersonType.OTHER,
    'Witness': PersonType.OTHER,
    '0': PersonType.OTHER,
}


def person_type(person):
    return PERSON_TYPE_TO_PERSON.get(person[PERSON_TYPE_COLUMN].strip())


def injury_type(person):
    if person['FATAL'] == 'Y':
        return InjuryType.FATALITY
    if person['MAJORINJURY'] == 'Y' or person['MINORINJURY'] == 'Y':
        return InjuryType.INJURY
    return InjuryType.NO_INJURY


def get_age(p):
    age = p['AGE']
    return 'unknown' if math.isnan(age) else int(age)


class DcApiDataInterface(ApiDataInterface):
    def __init__(self):
        super(DcApiDataInterface, self).__init__(entity='dc', tables=DC_TABLES)

    def convert_data_types(self, df, dataset: Table = None) -> None:
        if dataset.name == 'Crash':
            for col in INJURY_FATALITY_COLUMNS:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            df['FROMDATE'] = pd.to_datetime(df['FROMDATE'], errors='ignore')
            df['REPORTDATE'] = pd.to_datetime(df['REPORTDATE'], errors='ignore')

    def add_columns(self, df, dataset: Table) -> None:
        if dataset.name == 'Crash':
            df['FROMYEAR'] = pd.DatetimeIndex(df['FROMDATE']).year
            df['REPORTYEAR'] = pd.DatetimeIndex(df['REPORTDATE']).year

            def get_year(row):
                from_year = row['FROMYEAR']
                return row['REPORTYEAR'] if math.isnan(from_year) or from_year == 1900 else from_year

            df['YEAR'] = df.apply(lambda row: get_year(row), axis=1)
        return df

    def filter_rows(self, df, dataset: Table = None):
        filtered = df
        if dataset.name == 'Crash':
            filtered = filtered[filtered[INJURY_FATALITY_COLUMNS].sum(axis=1) > 0]
            filtered = filtered[filtered['LATITUDE'].notnull()]
            filtered = filtered[filtered['YEAR'].notnull()]
        return filtered


class DcRowDataGetter(RowDataGetter):
    @staticmethod
    def category(row):
        if type(row['Detail']) == float:
            return CrashCategory.OTHER.value
        injuries = map(lambda p: (injury_type(p), person_type(p)), row['Detail'])
        max_injury_person = max(injuries, key=lambda i: (i[0].value.severity, i[1].value.vulnerability))
        return max_injury_person[1].value.category.value

    @staticmethod
    def num_fatalities(row):
        return row[FATALITY_COLUMNS].sum()

    @staticmethod
    def num_vehicles(row):
        return row['TOTAL_VEHICLES']

    @staticmethod
    def injuries(row):
        injuries = defaultdict(list)
        if type(row['Detail']) == float:
            return injuries
        for p in row['Detail']:
            info = {
                'person': person_type(p).value.description,
                'age': get_age(p),
            }
            injuries[injury_type(p).value.category.value].append(info)
        return injuries


if __name__ == '__main__':
    api = DcApiDataInterface()
    # api.process_data()

    # person_df = pd.read_pickle(api.unfiltered_data_file(api.tables.detail.name, 'all'))

    print('Generating web data...')
    df = api.read_data()
    web_data_generator = WebDataGenerator(row_data_getter=DcRowDataGetter(column_names=COLUMN_NAMES),
                                          column_names=COLUMN_NAMES,
                                          data_description=DC_DATA_DESCRIPTION)

    web_data_generator.iterate_and_save(df, latlong_interval=1)
