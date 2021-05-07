import json

import pandas as pd
import requests
import geojson

BASE_URL = 'https://crashviewer.nhtsa.dot.gov'
CRASH_API = f'{BASE_URL}/CrashAPI/crashes'


def query_crash_api(api, params, cache=True):
    def get_filename():
        inner_name = None
        if api == 'GetCrashesByLocation':
            inner_name = 'GetCrashesByLocation'
        if api == 'GetCaseDetails':
            inner_name = f'GetCaseDetails-{params["caseYear"]}-{params["stateCase"]}'
        return f'cache/{inner_name}.json' if inner_name else None

    filename = get_filename()
    if cache and filename:
        try:
            with open(filename) as infile:
                return json.load(infile)
        except IOError:
            pass
    params['format'] = 'json'
    response = requests.get(f'{CRASH_API}/{api}', params=params).json()
    if cache and filename:
        with open(filename, 'w') as outfile:
            json.dump(response, outfile)
    return response


def convert_to_geojson(df):
    features = []
    harm_to_symbol = {
        'Motor Vehicle In-Transport': 'car',
        'Parked Motor Vehicle': 'car',
        'Pedalcyclist': 'bike',
        'Pedestrian': 'ped'
    }
    for index, row in df.iterrows():
        harm = row['Harm'].strip()
        features.append(geojson.Feature(geometry=geojson.Point((row['LONGITUD'], row['LATITUDE'])), properties={
            'year': row['CaseYear'],
            'case_id': row['ST_CASE'],
            'harm': harm_to_symbol[harm] if harm in harm_to_symbol else 'other',
        }))
    return geojson.FeatureCollection(features=features)


def get_people(crash_result_set):
    people = crash_result_set['NPersons'] or []
    for vehicle in crash_result_set['Vehicles']:
        people.extend(vehicle['Persons'])
    return people


def get_crashes_list(year_range=(2015, 2019), state_id=24, county_id=33):
    response = query_crash_api(api='GetCrashesByLocation',
                               params={'state': state_id, 'county': county_id, 'fromCaseYear': year_range[0],
                                       'toCaseYear': year_range[1]})

    df = pd.DataFrame(response['Results'][0])
    df[["LONGITUD", "LATITUDE"]] = df[["LONGITUD", "LATITUDE"]].apply(pd.to_numeric)

    bbox = (-76.9862, -76.7740, 39.0560, 38.9376)

    # df = df[(bbox[0] < df["LONGITUD"]) & (df["LONGITUD"] < bbox[1]) & (bbox[3] < df["LATITUDE"]) & (
    #         df["LATITUDE"] < bbox[2])]

    harm_column = 'Harm'
    metadata_column = 'Metadata'
    filter_column = 'Filter'
    df.insert(2, harm_column, value='')
    metadata = pd.DataFrame()
    for index, row in df.iterrows():
        response = query_crash_api(api='GetCaseDetails',
                                   params={'stateCase': row['ST_CASE'], 'caseYear': row['CaseYear'], 'state': state_id})
        crash_result_set = response['Results'][0][0]['CrashResultSet']
        df.at[index, metadata_column] = response['Results'][0][0]
        df.at[index, harm_column] = crash_result_set['HARM_EVNAME']
        df.at[index, filter_column] = any([int(p['INJ_SEV']) >= 4 for p in get_people(crash_result_set)])
        metadata.append(response['Results'][0][0]['CrashResultSet'], ignore_index=True)

    df = df[df['Filter']]

    with open('geojson.json', 'w') as outfile:
        json.dump(convert_to_geojson(df), outfile)


if __name__ == '__main__':
    get_crashes_list()
