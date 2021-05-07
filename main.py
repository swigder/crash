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
    for index, row in df.iterrows():
        features.append(geojson.Feature(geometry=geojson.Point((row['LONGITUD'], row['LATITUDE'])), properties={
            'year': row['CaseYear'],
            'case_id': row['ST_CASE'],
            'harm': get_category(row['People']),
            'injuries': list_injuries(row['People']),
            'num_vehicles': len(row['Vehicles']),
        }))
    return geojson.FeatureCollection(features=features)


def get_people(crash_result_set):
    people = crash_result_set['NPersons'] or []
    for vehicle in crash_result_set['Vehicles']:
        people.extend(vehicle['Persons'])
    return people


def get_category(people):
    per_typ_to_category = {v: k for k, values in {
        'car': [1, 2, 3, 4],
        'ped': [5, 8],
        'bike': [6],
        'other': [9, 10, 11],
    }.items() for v in values}

    max_category = 0
    max_inj_sev = 0
    for p in people:
        inj_sev = int(p['INJ_SEV'])
        category = int(p['PER_TYP'])
        if (inj_sev > max_inj_sev) or (inj_sev == max_inj_sev and category > max_category):
            max_category = category
            max_inj_sev = inj_sev
    return per_typ_to_category[max_category]


def list_injuries(people):
    injuries = []
    for p in people:
        injuries.append({'severity': p['INJ_SEVNAME'], 'person': p['PER_TYPNAME'].split()[0]})
    return injuries


def get_crashes_list(year_range=(2015, 2019), state_id=24, county_id=33):
    response = query_crash_api(api='GetCrashesByLocation',
                               params={'state': state_id, 'county': county_id, 'fromCaseYear': year_range[0],
                                       'toCaseYear': year_range[1]})

    df = pd.DataFrame(response['Results'][0])
    df[["LONGITUD", "LATITUDE"]] = df[["LONGITUD", "LATITUDE"]].apply(pd.to_numeric)

    people_column = 'People'
    vehicles_column = 'Vehicles'
    df.insert(2, people_column, value='')
    for index, row in df.iterrows():
        response = query_crash_api(api='GetCaseDetails',
                                   params={'stateCase': row['ST_CASE'], 'caseYear': row['CaseYear'], 'state': state_id})
        crash_result_set = response['Results'][0][0]['CrashResultSet']
        df.at[index, people_column] = get_people(crash_result_set)
        df.at[index, vehicles_column] = crash_result_set['Vehicles']

    with open('geojson.json', 'w') as outfile:
        json.dump(convert_to_geojson(df), outfile)


if __name__ == '__main__':
    get_crashes_list()
