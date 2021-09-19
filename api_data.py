import glob
from dataclasses import dataclass

import pandas as pd


@dataclass
class Table:
    name: str
    columns: list


@dataclass
class Tables:
    key_columns: list[str]
    crash: Table
    person: Table
    vehicle: Table

    def get_tables(self):
        return [self.crash, self.person, self.vehicle]


class ApiDataInterface:
    def __init__(self, state, tables: Tables):
        self.state = state
        self.tables = tables
        self.key_columns = self.tables.key_columns

    def data_dir(self):
        return f'data.nosync/{self.state}'

    def unfiltered_data_file(self, dataset_name, year):
        return f'{self.data_dir()}/{dataset_name}-{year}.pkl'

    def filtered_data_file(self, dataset_name, year):
        return f'{self.data_dir()}/{dataset_name}-{year}-filtered.pkl'

    def merged_data_file(self, year):
        return f'{self.data_dir()}/data-{year}.pkl'

    def convert_to_df(self):
        pass

    def filter_columns(self, df, dataset: Table):
        return df[self.key_columns + dataset.columns]

    def filter_rows(self, df, dataset: Table = None):
        return df

    def convert_data_types(self, df, dataset: Table = None) -> None:
        return

    def merge_data(self, year):
        crash_df = pd.read_pickle(self.filtered_data_file(self.tables.crash.name, year))
        crash_df.columns = [c.upper() for c in crash_df.columns]
        crash_df = crash_df.set_index(self.key_columns, drop=True)

        person_df = pd.read_pickle(self.filtered_data_file(self.tables.person.name, year))
        person_df = person_df.groupby(self.key_columns)[person_df.columns.difference(self.key_columns)].apply(
            lambda x: x.to_dict('r'))

        vehicle_df = pd.read_pickle(self.filtered_data_file(self.tables.vehicle.name, year))
        vehicle_df = vehicle_df.groupby(self.key_columns).size()

        df = crash_df. \
            merge(person_df.rename('Person'), how='left', left_index=True, right_index=True). \
            merge(vehicle_df.rename('Vehicle'), how='left', left_index=True, right_index=True)

        df.to_pickle(self.merged_data_file(year))

    def filter_data(self, year):
        for dataset in self.tables.get_tables():
            dataset_name = dataset.name
            df = pd.read_pickle(self.unfiltered_data_file(dataset_name, year))
            self.convert_data_types(df, dataset)
            df = self.filter_columns(df, dataset)
            df = self.filter_rows(df, dataset)
            df.to_pickle(self.filtered_data_file(dataset_name, year))

    def process_data(self, year):
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
