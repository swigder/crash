import glob
import json

import pandas as pd
import requests

from generate_geojson import convert_to_geojson

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


KEY_COLUMNS = ['CASEYEAR', 'STATE', 'ST_CASE']

DATASETS = {
    'Accident': ['LATITUDE', 'LONGITUD'],
    'Person': ['PER_TYP', 'PER_TYPNAME', 'INJ_SEV', 'INJ_SEVNAME'],
    'Vehicle': [],
}


def refresh_data_from_server(year):
    for dataset, _ in DATASETS.items():
        query_fars_api(api=f'{DATA_API}/GetFARSData', params={'dataset': dataset, 'caseYear': year},
                       force_cache_update=True)


def filter_data(year):
    for dataset, fields in DATASETS.items():
        response = query_fars_api(api=f'{DATA_API}/GetFARSData',
                                  params={'dataset': dataset, 'caseYear': year})
        df = pd.DataFrame(response['Results'][0])
        df.columns = [c.upper() for c in df.columns]
        df = df[KEY_COLUMNS + fields]
        with open(f'data/{dataset}-{year}.csv', 'w') as outfile:
            df.to_csv(outfile, index=False)


def merge_data(year):
    crash_df = pd.read_csv(f'data/Accident-{year}.csv')
    crash_df.columns = [c.upper() for c in crash_df.columns]
    crash_df = crash_df.set_index(KEY_COLUMNS, drop=True)

    person_df = pd.read_csv(f'data/Person-{year}.csv')
    person_df = person_df.groupby(KEY_COLUMNS)[person_df.columns.difference(KEY_COLUMNS)].apply(
        lambda x: x.to_dict('r'))

    vehicle_df = pd.read_csv(f'data/Vehicle-{year}.csv')
    vehicle_df = vehicle_df.groupby(KEY_COLUMNS).size()

    df = crash_df.\
        merge(person_df.rename('Person'), how='left', left_index=True, right_index=True).\
        merge(vehicle_df.rename('Vehicle'), how='left', left_index=True, right_index=True)

    df.to_pickle(f'data/df-{year}.pkl')


def generate_geojson():
    all_pickles = glob.glob('data/df-*.pkl')
    dfs = []
    for filename in all_pickles:
        df = pd.read_pickle(filename)
        dfs.append(df)
    df = pd.concat(dfs, axis=0)

    grouped = df.groupby(
        df[['LATITUDE', 'LONGITUD']].agg(lambda ys: '_'.join([str(int(y / 2)*2) for y in ys]), axis=1))
    for name, group in grouped:
        with open(f'geojson/geojson-{name}.json', 'w') as outfile:
            json.dump(convert_to_geojson(group.reset_index()), outfile)


if __name__ == '__main__':
    years = range(2010, 2015)
    for _year in years:
        refresh_data_from_server(year=_year)
        filter_data(year=_year)
        merge_data(year=_year)
        pass
    generate_geojson()
