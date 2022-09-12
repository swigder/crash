import glob
import os
from dataclasses import dataclass

import pandas as pd
import requests


@dataclass
class Table:
    name: str
    columns: list
    url: str = None


@dataclass
class Tables:
    key_columns: list[str]
    crash: Table
    person: Table = None
    vehicle: Table = None
    detail: Table = None

    def get_tables(self):
        return [t for t in [self.crash, self.person, self.vehicle, self.detail] if t]


@dataclass
class DataSources:
    crash: str


class ApiDataInterface:
    def __init__(self, entity, tables: Tables):
        self.entity = entity
        self.tables = tables
        self.key_columns = self.tables.key_columns

    def data_dir(self):
        return f'data.nosync/{self.entity}'

    def downloaded_data_file(self, dataset_name):
        return f'{self.data_dir()}/{dataset_name.lower()}.csv'

    def unfiltered_data_file(self, dataset_name, year):
        return f'{self.data_dir()}/{dataset_name}-{year}.pkl'

    def filtered_data_file(self, dataset_name, year):
        return f'{self.data_dir()}/{dataset_name}-{year}-filtered.pkl'

    def merged_data_file(self, year):
        return f'{self.data_dir()}/data-{year}.pkl'

    def download_data(self, refresh=False):
        if not os.path.exists(self.data_dir()):
            os.makedirs(self.data_dir())
        for table in self.tables.get_tables():
            if not table.url:
                continue
            output_path = self.downloaded_data_file(table.name)
            if not refresh and os.path.exists(output_path):
                continue
            response = requests.get(table.url)
            response.encoding = 'utf-8-sig'
            with open(output_path, 'w') as outfile:
                outfile.write(response.text)

    def convert_to_df(self):
        for table in self.tables.get_tables():
            df = pd.read_csv(self.downloaded_data_file(table.name))
            df.to_pickle(self.unfiltered_data_file(table.name, year='all'))

    def convert_data_types(self, df, dataset: Table = None) -> None:
        return

    def add_columns(self, df, dataset: Table) -> None:
        return df

    def filter_columns(self, df, dataset: Table):
        return df[self.key_columns + dataset.columns]

    def filter_rows(self, df, dataset: Table = None):
        return df

    def filter_data(self, year):
        for dataset in self.tables.get_tables():
            dataset_name = dataset.name
            df = pd.read_pickle(self.unfiltered_data_file(dataset_name, year))
            df.columns = [c.upper() for c in df.columns]
            self.convert_data_types(df, dataset)
            df = self.add_columns(df, dataset)
            df = self.filter_columns(df, dataset)
            df = self.filter_rows(df, dataset)
            df.to_pickle(self.filtered_data_file(dataset_name, year))

    def merge_data(self, year):
        crash_df = pd.read_pickle(self.filtered_data_file(self.tables.crash.name, year))
        crash_df.columns = [c.upper() for c in crash_df.columns]
        crash_df = crash_df.set_index(self.key_columns, drop=True)

        merged_df = crash_df

        for other_table in self.tables.get_tables():
            if not other_table or other_table.name == 'Crash':
                continue
            other_df = pd.read_pickle(self.filtered_data_file(other_table.name, year))
            other_df = other_df.groupby(self.key_columns)[other_df.columns.difference(self.key_columns)].apply(lambda x: x.to_dict('r'))
            merged_df = merged_df.merge(other_df.rename(other_table.name), how='left', left_index=True, right_index=True)

        merged_df.to_pickle(self.merged_data_file(year))

    def process_data(self, year='all'):
        print('Downloading data...')
        self.download_data(refresh=False)
        print('Converting to df...')
        self.convert_to_df()
        print('Filtering...')
        self.filter_data(year)
        print('Merging...')
        self.merge_data(year)
        print('Done.')

    def read_data(self):
        all_pickles = glob.glob(self.merged_data_file('*'))
        dfs = []
        for filename_geojson in all_pickles:
            df = pd.read_pickle(filename_geojson)
            dfs.append(df)
        return pd.concat(dfs, axis=0)
