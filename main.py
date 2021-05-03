import pandas as pd
import requests
import matplotlib.pyplot as plt


def get_crashes_list(year_range=(2015, 2019), state_id=24, county_id=33):
    response = requests.get('https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCrashesByLocation',
                            params={'state': state_id, 'county': county_id, 'fromCaseYear': year_range[0], 'toCaseYear': year_range[1],
                                    'format': 'json'})
    df = pd.DataFrame(response.json()['Results'][0])
    df[["LONGITUD", "LATITUDE"]] = df[["LONGITUD", "LATITUDE"]].apply(pd.to_numeric)

    bbox = (-76.9862, -76.7740, 39.0560, 38.9376)

    ndf = df[(bbox[0] < df["LONGITUD"]) & (df["LONGITUD"] < bbox[1]) & (bbox[3] < df["LATITUDE"]) & (df["LATITUDE"] < bbox[2])]

    with plt.style.context('seaborn-white'):
        fig, ax = plt.subplots(dpi=600)
        ax.scatter(df.LONGITUD, df.LATITUDE, zorder=1, alpha=0.8, s=10)

        ax.set_xlim(bbox[0], bbox[1])
        ax.set_ylim(bbox[3], bbox[2])
        image = plt.imread('map.png')
        ax.imshow(image, zorder=0, extent=bbox, aspect='equal', interpolation='none', origin='lower')

        plt.show()


if __name__ == '__main__':
    get_crashes_list()
