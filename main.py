import glob
import json

import pandas as pd
import requests

from api_data import ApiDataInterface, Table, Tables
from fars import COLUMN_NAMES, FARS_DATA_DESCRIPTION
from fars import FarsRowDataGetter
from web_data import WebDataGenerator

BASE_URL = 'https://crashviewer.nhtsa.dot.gov/CrashAPI'
CRASH_API = f'{BASE_URL}/crashes'
DATA_API = f'{BASE_URL}/FARSData'


def query_fars_api(api, params, force_cache_update=False):
    def get_filename():
        inner_name = None
        if api == 'GetCrashesByLocation':
            inner_name = 'GetCrashesByLocation'
        elif api == 'GetCaseDetails':
            inner_name = f'GetCaseDetails-{params["caseYear"]}-{params["stateCase"]}'
        elif api == 'GetFARSData':
            inner_name = f'GetFARSData-{params["dataset"]}-{params["caseYear"]}'
        return f'cache/{inner_name}.json' if inner_name else None

    filename = get_filename()
    if not force_cache_update and filename:
        try:
            with open(filename) as infile:
                return json.load(infile)
        except IOError:
            pass
    params['format'] = 'json'
    response = requests.get(api, params=params).json()
    if filename:
        with open(filename, 'w') as outfile:
            json.dump(response, outfile)
    return response


FARS_TABLES = Tables(
    key_columns=['CASEYEAR', 'STATE', 'ST_CASE'],
    crash=Table(name='Accident', columns=['LATITUDE', 'LONGITUD', 'FATALS']),
    person=Table(name='Person', columns=['PER_TYP', 'PER_TYPNAME', 'INJ_SEV', 'INJ_SEVNAME', 'AGE']),
    vehicle=Table(name='Vehicle', columns=[]),
)


def refresh_data_from_server(year):
    for dataset, _ in DATASETS:
        query_fars_api(api=f'{DATA_API}/GetFARSData', params={'dataset': dataset.name, 'caseYear': year},
                       force_cache_update=True)


def convert_to_df(year):
    for dataset, fields in DATASETS:
        response = query_fars_api(api=f'{DATA_API}/GetFARSData',
                                  params={'dataset': dataset, 'caseYear': year})
        df = pd.DataFrame(response['Results'][0])
        df.columns = [c.upper() for c in df.columns]
        df.to_pickle(f'data/{dataset}-{year}.pkl')


class FarsApiDataInterface(ApiDataInterface):
    def __init__(self):
        super(FarsApiDataInterface, self).__init__(state='fars', tables=FARS_TABLES)

    def convert_to_df(self):
        pass

    def convert_data_types(self, df, dataset: Table = None):
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')


def generate_web_data():
    df = FarsApiDataInterface().read_data()

    web_data_generator = WebDataGenerator(row_data_getter=FarsRowDataGetter(),
                                          column_names=COLUMN_NAMES,
                                          data_description=FARS_DATA_DESCRIPTION)
    web_data_generator.iterate_and_save(df, latlong_interval=2)


if __name__ == '__main__':
    years = range(2010, 2019)
    for _year in years:
        print(f'Starting year {_year}...')
        # print('Refreshing data...')
        # refresh_data_from_server(year=_year)
        # print('Converting data to df...')
        # convert_to_df(year=_year)
        # print('Filtering data...')
        # filter_data(year=_year)
        # print('Merging data...')
        # merge_data(year=_year)
        pass
    print('Generating web data...')
    generate_web_data()
    print('Done.')
