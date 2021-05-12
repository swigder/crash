import geojson


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


def get_injuries(people):
    injuries = []
    for p in people:
        injuries.append({'severity': p['INJ_SEVNAME'], 'person': p['PER_TYPNAME'].split()[0]})
    return injuries


def get_num_fatalities(people):
    num_fatalities = 0
    for p in people:
        if int(p['INJ_SEV']) >= 4:
            num_fatalities += 1
    return num_fatalities


def convert_to_geojson(df):
    features = []
    for index, row in df.iterrows():
        features.append(geojson.Feature(geometry=geojson.Point((row['LONGITUD'], row['LATITUDE'])), properties={
            'year': row['CaseYear'],
            'case_id': row['ST_CASE'],
            'harm': get_category(row['People']),
            'injuries': get_injuries(row['People']),
            'num_vehicles': len(row['Vehicles']),
            'num_fatalities': get_num_fatalities(row['People']),
        }))
    return geojson.FeatureCollection(features=features)
