import geojson


def get_category(people):
    per_typ_to_category = {v: k for k, values in {
        'car': [1, 2, 3, 4],
        'ped': [5, 8],
        'bike': [6, 7],
        'other': [9, 10, 19],
    }.items() for v in values}

    max_category = 0
    max_inj_sev = 0
    for p in people:
        inj_sev = max(int(p['INJ_SEV']), 4)
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


def convert_to_web_data(df):
    items = []
    for index, row in df.iterrows():
        items.append({
            'latlng': [row['LATITUDE'], row['LONGITUD']],
            'data': {
                'year': row['CASEYEAR'],
                'case_id': row['ST_CASE'],
                'harm': get_category(row['Person']),
                'injuries': get_injuries(row['Person']),
                'num_vehicles': row['Vehicle'],
                'num_fatalities': get_num_fatalities(row['Person']),
            },
        })
    return items