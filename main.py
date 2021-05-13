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


def refresh_data_from_server(years):
    for year in years:
        for dataset, _ in DATASETS.items():
            query_fars_api(api=f'{DATA_API}/GetFARSData', params={'dataset': dataset, 'caseYear': year},
                           force_cache_update=True)


def filter_data(years):
    for year in years:
        for dataset, fields in DATASETS.items():
            response = query_fars_api(api=f'{DATA_API}/GetFARSData',
                                      params={'dataset': dataset, 'caseYear': year})
            df = pd.DataFrame(response['Results'][0])
            df.columns = [c.upper() for c in df.columns]
            df = df[KEY_COLUMNS + fields]
            with open(f'data/{dataset}-{year}.csv', 'w') as outfile:
                df.to_csv(outfile, index=False)


def save_by_latlong(years):
    for year in years:
        crash_df = pd.read_csv(f'data/Accident-{year}.csv')
        crash_df.columns = [c.upper() for c in crash_df.columns]
        crash_df = crash_df.set_index(KEY_COLUMNS, drop=True)
        person_df = pd.read_csv(f'data/Person-{year}.csv')
        person_df = person_df.groupby(KEY_COLUMNS)[person_df.columns.difference(KEY_COLUMNS)].apply(
            lambda x: x.to_dict('r'))
        df = crash_df.merge(person_df.rename('Person'), how='left', left_index=True, right_index=True)
        grouped = df.groupby(
            df[['LATITUDE', 'LONGITUD']].agg(lambda ys: '_'.join([str(int(y)) for y in ys]), axis=1))
        for name, group in grouped:
            with open(f'data/data-{year}-{name}.json', 'w') as outfile:
                group.reset_index().to_json(outfile, orient='records')


if __name__ == '__main__':
    data_years = range(2015, 2020)
    # refresh_data_from_server(years=data_years)
    # filter_data(years=data_years)
    save_by_latlong(years=data_years)
