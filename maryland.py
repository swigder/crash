import pandas as pd

from api_data import ApiDataInterface
from web_data import ColumnNames, WebDataGenerator, RowDataGetter, DataDescription

WEB_BASE_DIR = 'web'
DATA_BASE_DIR = 'data/maryland'

COLUMNS = ['REPORT_NO', 'REPORT_TYPE', 'HARM_EVENT_DESC1', 'HARM_EVENT_DESC2', 'LATITUDE', 'LONGITUDE', 'YEAR']

HARM = {
    'Pedestrian': 'ped',
    'Bicycle': 'bike',
}

COLUMN_NAMES = ColumnNames(latitude='LATITUDE', longitude='LONGITUDE', year='YEAR')


MARYLAND_DATA_DESCRIPTION = DataDescription(
    title='Crashes with Injuries or Fatalities in Maryland',
    source='Maryland State Police <a href="https://opendata.maryland.gov/Public-Safety/Maryland-Statewide-Vehicle'
           '-Crashes/65du-s3qu">Maryland Statewide Vehicle Crashes</a>. Data is updated quarterly.',
    state='maryland',
)


class MarylandApiDataInterface(ApiDataInterface):
    def convert_to_df(self):
        df = pd.read_csv('data/Maryland_Statewide_Vehicle_Crashes.csv')
        df.to_pickle('data/maryland.pkl')

    def filter_data(self):
        df = pd.read_pickle(f'data/maryland.pkl')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        df = df[COLUMNS]
        df = df.loc[(df['REPORT_TYPE'] == 'Fatal Crash') | (df['REPORT_TYPE'] == 'Injury Crash')]
        df.to_pickle(f'data/maryland-filtered.pkl')

    def read_data(self):
        return pd.read_pickle(f'data/maryland-filtered.pkl')


class MarylandRowDataGetter(RowDataGetter):
    @staticmethod
    def item_id(row):
        return row['REPORT_NO']

    @staticmethod
    def category(row):
        return HARM.get(row['HARM_EVENT_DESC1'], 'car')


def generate_web_data():
    df = MarylandApiDataInterface().read_data()

    web_data_generator = WebDataGenerator(row_data_getter=MarylandRowDataGetter(),
                                          column_names=COLUMN_NAMES,
                                          data_description=MARYLAND_DATA_DESCRIPTION)
    web_data_generator.iterate_and_save(df, latlong_interval=2)


if __name__ == '__main__':
    # convert_to_df()
    # filter_data()
    # df = pd.read_pickle(f'data/maryland-filtered.pkl')
    print('Generating web data...')
    generate_web_data()
    print('Done.')
