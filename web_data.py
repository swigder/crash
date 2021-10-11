import json
import math
import os

import geojson
import pandas as pd
from dataclasses import dataclass

WEB_BASE_DIR = 'web'
DATA_BASE_DIR = 'data'


@dataclass
class ColumnNames:
    latitude: str = 'LATITUDE'
    longitude: str = 'LONGITUDE'
    year: str = 'YEAR'
    id: str = None


@dataclass
class Links:
    crash_format: str
    person_format: str = None
    vehicle_format: str = None
    id_splitter: str = None


@dataclass
class DataDescription:
    title: str
    source: str
    state: str
    record_links: Links


class RowDataGetter:
    def __init__(self, column_names: ColumnNames = None):
        self.column_names = column_names

    def item_id(self, row):
        return row[self.column_names.id] if self.column_names.id else None

    @staticmethod
    def category(row):
        pass

    @staticmethod
    def num_fatalities(row):
        pass

    @staticmethod
    def num_vehicles(row):
        pass

    @staticmethod
    def injuries(row):
        return {}


class WebDataGenerator:
    def __init__(self, row_data_getter: RowDataGetter, column_names: ColumnNames, data_description: DataDescription):
        self.column_names = column_names
        self.row_data_getter = row_data_getter
        self.data_description = data_description
        self.data_dir = f'data/{data_description.state}'
        self.web_data_dir = f'{WEB_BASE_DIR}/{self.data_dir}'
        if not os.path.exists(self.web_data_dir):
            os.makedirs(self.web_data_dir)

    def iterate_and_save(self, df, latlong_interval: int = 1):
        grouped = df.groupby(
            df[[self.column_names.latitude, self.column_names.longitude]].agg(
                lambda ys: '_'.join([str(math.floor(y / latlong_interval) * latlong_interval) for y in ys]), axis=1))

        filenames = []
        for name, group in grouped:
            groupdf = group.reset_index()

            geojson_items = []
            items_details = {}
            for index, row in groupdf.iterrows():
                item_id = str(self.row_data_getter.item_id(row))
                year = int(row[self.column_names.year])
                properties = {
                    'id': item_id,
                    'year': year,
                    'harm': self.row_data_getter.category(row),
                    'num_fatalities': self.row_data_getter.num_fatalities(row),
                }
                details = {
                    'year': year,
                    'num_vehicles': self.row_data_getter.num_vehicles(row),
                }
                details.update(self.row_data_getter.injuries(row))
                geojson_items.append(
                    geojson.Feature(geometry=geojson.Point((row[self.column_names.longitude], row[self.column_names.latitude])), properties=properties))

                items_details[item_id] = details

            filename_geojson = f'{self.data_dir}/data-{name}.json'
            with open(f'{WEB_BASE_DIR}/{filename_geojson}', 'w') as outfile:
                json.dump(geojson.FeatureCollection(features=geojson_items), outfile)
            filenames.append(filename_geojson)
            filename_full = f'{self.data_dir}/data-{name}-full.json'
            with open(f'{WEB_BASE_DIR}/{filename_full}', 'w') as outfile:
                json.dump(items_details, outfile)

        df = df.reset_index()
        for col in [self.column_names.year]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        metadata = {
            'title': self.data_description.title,
            'source': self.data_description.source,
            'latlong_interval': latlong_interval,
            'min_year': int(df[self.column_names.year].min()),
            'max_year': int(df[self.column_names.year].max()),
            'filenames': filenames,
            'record_links': {
                'id_splitter': self.data_description.record_links.id_splitter,
                'crash_format': self.data_description.record_links.crash_format,
                'person_format': self.data_description.record_links.person_format,
                'vehicle_format': self.data_description.record_links.vehicle_format,
            }
        }

        with open(f'{self.web_data_dir}/file-metadata.json', 'w') as outfile:
            json.dump(metadata, outfile)

