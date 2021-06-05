import glob
import json
import math

import pandas as pd
import requests

from generate_web_data import convert_to_web_data

BASE_URL = 'https://crashviewer.nhtsa.dot.gov/CrashAPI'
CRASH_API = f'{BASE_URL}/crashes'
DATA_API = f'{BASE_URL}/FARSData'

WEB_BASE_DIR = 'web'
DATA_BASE_DIR = 'data'


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


KEY_COLUMNS = ['CASEYEAR', 'STATE', 'ST_CASE']

DATASETS = {
    'Accident': ['LATITUDE', 'LONGITUD', 'FATALS'],
    'Person': ['PER_TYP', 'PER_TYPNAME', 'INJ_SEV', 'INJ_SEVNAME', 'AGE'],
    'Vehicle': [],
}


def refresh_data_from_server(year):
    for dataset, _ in DATASETS.items():
        query_fars_api(api=f'{DATA_API}/GetFARSData', params={'dataset': dataset, 'caseYear': year},
                       force_cache_update=True)


def convert_to_df(year):
    for dataset, fields in DATASETS.items():
        response = query_fars_api(api=f'{DATA_API}/GetFARSData',
                                  params={'dataset': dataset, 'caseYear': year})
        df = pd.DataFrame(response['Results'][0])
        df.columns = [c.upper() for c in df.columns]
        df.to_pickle(f'data/{dataset}-{year}.pkl')


def filter_data(year):
    for dataset, fields in DATASETS.items():
        df = pd.read_pickle(f'data/{dataset}-{year}.pkl')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        df = df[KEY_COLUMNS + fields]
        df.to_pickle(f'data/{dataset}-{year}-filtered.pkl')


def merge_data(year):
    crash_df = pd.read_pickle(f'data/Accident-{year}-filtered.pkl')
    crash_df.columns = [c.upper() for c in crash_df.columns]
    crash_df = crash_df.set_index(KEY_COLUMNS, drop=True)

    person_df = pd.read_pickle(f'data/Person-{year}-filtered.pkl')
    person_df = person_df.groupby(KEY_COLUMNS)[person_df.columns.difference(KEY_COLUMNS)].apply(
        lambda x: x.to_dict('r'))

    vehicle_df = pd.read_pickle(f'data/Vehicle-{year}-filtered.pkl')
    vehicle_df = vehicle_df.groupby(KEY_COLUMNS).size()

    df = crash_df. \
        merge(person_df.rename('Person'), how='left', left_index=True, right_index=True). \
        merge(vehicle_df.rename('Vehicle'), how='left', left_index=True, right_index=True)

    df.to_pickle(f'data/df-{year}.pkl')


def generate_web_data():
    all_pickles = glob.glob('data/df-*.pkl')
    dfs = []
    for filename_geojson in all_pickles:
        df = pd.read_pickle(filename_geojson)
        dfs.append(df)
    df = pd.concat(dfs, axis=0)

    latlong_interval = 2

    grouped = df.groupby(
        df[['LATITUDE', 'LONGITUD']].agg(
            lambda ys: '_'.join([str(math.floor(y / latlong_interval) * latlong_interval) for y in ys]), axis=1))
    filenames = []
    for name, group in grouped:
        groupdf = group.reset_index()
        geojson, full = convert_to_web_data(groupdf)
        filename_geojson = f'{DATA_BASE_DIR}/data-{name}.json'
        with open(f'{WEB_BASE_DIR}/{filename_geojson}', 'w') as outfile:
            json.dump(geojson, outfile)
        filenames.append(filename_geojson)
        filename_full = f'{DATA_BASE_DIR}/data-{name}-full.json'
        with open(f'{WEB_BASE_DIR}/{filename_full}', 'w') as outfile:
            json.dump(full, outfile)

    df = df.reset_index()
    for col in ['CASEYEAR']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    metadata = {
        'latlong_interval': latlong_interval,
        'min_year': int(df['CASEYEAR'].min()),
        'max_year': int(df['CASEYEAR'].max()),
        'filenames': filenames,
    }

    with open(f'{WEB_BASE_DIR}/{DATA_BASE_DIR}/file-metadata.json', 'w') as outfile:
        json.dump(metadata, outfile)


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
