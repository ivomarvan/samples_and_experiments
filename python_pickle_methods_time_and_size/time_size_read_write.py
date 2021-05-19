#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Test_time_and_size_pickle_methods

    It tests different data storage methods (feather, sql, csv, hdf, pickle, parquet) 
    for different types (gzip, bz2, zip, xz) 
    and compression levels (0-9).

    Measures read/write times and size for a given number of experiments (parameter -e) on a test file (parameter -i).
    
    (MIT License)
'''

import os
import sys
import pandas as pd
import numpy as np
from timeit import Timer
from numpy import round, nan, isnan
from itertools import product
import argparse

# root of repository in your filesystem
THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(THIS_FILE_DIR)


# --- from http://pandas.pydata.org/pandas-docs/stable/io.html#performance-considerations -----------------------------
import sqlite3

# method => variants of parameters
fn_descriptions = {
    'feather': {},
    'sql': {},
    'csv': {
        'compression': [None, 'gzip', 'bz2', 'zip', 'xz']
    },
    'hdf': {
        'complevel': range(10),
        'complib': ['zlib', 'lzo', 'bzip2', 'blosc'],
        'format': ['table', 'fixed']
    },
    'csv': {
        'compression': [None, 'gzip', 'bz2', 'zip', 'xz']
    },
    'pickle': {
        'protocol': range(5),
        'compression': [None, 'gzip', 'bz2', 'zip', 'xz']
    },
    'parquet': {
        'engine' : ['auto', 'pyarrow', 'fastparquet'],
        'compression' : ['snappy', 'gzip', 'brotli', None],
    },
}

# @ todo add to_parquet


def test_sql_write(df, filename):
    if os.path.exists(filename):
        os.remove(filename)
    sql_db = sqlite3.connect(filename)
    df.to_sql(name='test_table', con=sql_db)
    sql_db.close()


def test_sql_read(filename):
    sql_db = sqlite3.connect(filename)
    ret = pd.read_sql_query("select * from test_table", sql_db)
    sql_db.close()
    return ret


def test_hdf_write(df, filename, complib, complevel, format):
    df.to_hdf(filename, 'test', mode='w', complib=complib, complevel=complevel, format=format)


def test_hdf_read(filename, complib, complevel, format):
    return pd.read_hdf(filename, 'test')


def test_csv_write(df, filename, compression=None):
    df.to_csv(filename, mode='w', compression=compression)


def test_csv_read(filename, compression=None):
    return pd.read_csv(filename, index_col=0, compression=compression)


def test_parquet_write(df, filename, engine, compression):
    df.to_parquet(filename, engine=engine, compression=compression)


def test_parquet_read(filename, engine, compression):
    return pd.read_parquet(filename, engine=engine)


def test_feather_write(df, filename):
    df.to_feather(filename)


def test_feather_read(filename):
    return pd.read_feather(filename)


def test_pickle_write(df, filename, protocol, compression):
    df.to_pickle(filename, protocol=protocol, compression=compression)


def test_pickle_read(filename, protocol, compression):
    return pd.read_pickle(filename, compression=compression)
# ----------------------------------------------------------------------------------------------------------------------


def get_file_size(file_path):
    if not os.path.isfile(file_path):
        return nan
    file_info = os.stat(file_path)
    return file_info.st_size


def get_params_variant(params:dict):
    '''
    Returns (yields) all variants of params
    '''
    sources = []
    for param_name, iterable_values in params.items():
        sources.append(iterable_values)
    products = product(*sources)
    for one_product in products:
        ret_dict = {}
        for i, param_name in enumerate(params):
            ret_dict[param_name] = one_product[i]
        yield ret_dict


def get_filename_kind_params_id(outdir:str, fn_descriptions:dict=fn_descriptions) -> (str, str, str):
    '''
    Yield (filename, fuction_call_string)
    '''
    for kind, params_desr in fn_descriptions.items():
        for params_dict in get_params_variant(params_desr):
            filename = os.path.join(outdir, 'test.' + kind)
            params_str = ''
            id_str = kind
            for key, value in params_dict.items():
                filename += '.' + key + '=' + str(value)
                params_str += ', ' + key
                id_str += '.' + key + '_' + str(value)
                if isinstance(value, str):
                    params_str += '="' + value + '"'
                else:
                    params_str += '=' + str(value)
            yield filename, kind, params_str, id_str


def get_time_size(
        df: pd.DataFrame,
        outdir: str,
        number_of_experiments: int = 5,
        fn_descriptions: dict=fn_descriptions
) -> pd.DataFrame:

    columns = ['id', 'write_time', 'read_time', 'size']
    rows = []
    t = nan
    for filename, kind, params_str, id_str in get_filename_kind_params_id(outdir, fn_descriptions):
        row = [id_str]
        print(id_str)
        for direction in ['write', 'read']:
            sys.stdout.write('\t' + direction + ':')
            function_call_str = 'test_' + kind + '_' + direction
            if direction == 'write':
                function_call_str += '(df, filename'
            else:
                function_call_str += '(filename'
            function_call_str += params_str + ')'
            setup = 'filename = "{}"'.format(filename)
            t = nan
            try:
                timer = Timer(stmt=function_call_str, setup=setup, globals=globals())
                t = timer.timeit(number=number_of_experiments)
            except Exception as e:
                sys.stderr.write(str(e) + '\n')
            except:
                sys.stderr.write(str(e) + '\n')
            print(t)
            row.append(t)
        if t and not isnan(t):
            # reading was sucessful
            size = get_file_size(filename)
        else:
            size = nan
        row.append(size)
        print('\tsize:', str(size))
        rows.append(row)
    return pd.DataFrame(data=rows, columns=columns)


def process_size_time(df:pd.DataFrame)->pd.DataFrame:
    '''
    Add relative values
    '''
    for c in ['write_time', 'read_time', 'size']:
        df['rel_' + c] = round(df[c] / df[c].min(),1)
    df['rel_sum'] = df['rel_write_time'] + df['rel_read_time'] + df['rel_size']
    df.sort_values(by='rel_sum', inplace=True)
    return df


def print_masters(df:pd.DataFrame):
    for c in ['write_time', 'read_time', 'size']:
        c1 = 'rel_' + c
        print('Master for "{}":\t\t{}'.format(c, list(df[df[c1]==1]['id'])))
    print('Master of compromise:\t\t{}'.format(list(df[df['rel_sum']==df['rel_sum'].min()]['id'])))


def read_sample_data(in_filename:str) -> pd.DataFrame:
    '''
    For different type o data you can change this function.
    For examle:
        df = pd.read_csv(
            in_filename,
            sep=';',
            compression='gzip',
            header=0,
            index_col=0,
            decimal=','
        )
        # reformat index to datetime
        df.index = pd.to_datetime(df.index, format='%d.%m.%Y %H:%M:%S.000')
        # force double precision
        df = df.astype(np.float64)
        return df
    '''
    return pd.read_csv(in_filename, compression='gzip', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__description__)

    default = os.path.join(THIS_FILE_DIR, 'data', 'in', 'data.csv.gz')
    parser.add_argument(
        '-i', '--infile',
        dest = 'infile',
        metavar = '<infile>',
        type = str,
        required = False,
        default = default,
        help = 'input gziped csv file with test data (default:' + str(default) + ')'
    )

    default = os.path.join(THIS_FILE_DIR, 'data', 'out')
    parser.add_argument(
        '-od', '--outdir',
        dest='outdir',
        metavar='<outdir>',
        type=str,
        required=False,
        default=default,
        help='output directory for result (default:' + str(default) + ')'
    )

    default = 5
    parser.add_argument(
        '-e', '--number_of_experiments',
        dest='number_of_experiments',
        metavar='<number_of_experiments>',
        type=int,
        required=False,
        default=default,
        help='number of experiments for avarage for one methode (default:' + str(default) + ')'
    )

    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    result_filename = os.path.join(args.outdir, 'results.csv')
    df = read_sample_data(args.infile)
    time_size_table = get_time_size(
        df, number_of_experiments=args.number_of_experiments, outdir=args.outdir, fn_descriptions=fn_descriptions
    )
    time_size_table = process_size_time(time_size_table)
    test_csv_write(time_size_table, result_filename)
    print('-'*80)
    print_masters(time_size_table)
    print('-' * 80)
