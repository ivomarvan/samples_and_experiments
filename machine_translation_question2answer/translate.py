#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "ivo@marvan.cz"
__description__ = '''
Automatic translation for web https://www.question2answer.org/ to local language.

Translate *.php files by google, deepl, ...
Read ./README.md for details
'''
import os
import re
import sys
import argparse
from pprint import pprint

# root of repository in your filesystem
THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(THIS_FILE_DIR)

from languages import LANGUAGES

DATA_DIR = os.path.realpath(os.path.join(THIS_FILE_DIR, 'data'))
IN_DIR = os.path.join(DATA_DIR, 'orig')
OUT_DIR = os.path.join(DATA_DIR, 'outputs')

HEADER_RE = re.compile(r'.*array\(', re.DOTALL)
TAIL_RE = re.compile(r'\);[\s]+', re.DOTALL)
COMMENT_RE = re.compile(r',(  \/\/.*)')

def decompose_php_source(source: str) -> (str, dict, str):
    match = HEADER_RE.match(source)
    start, end = match.regs[0]
    header = source[start:end]
    rest= source[end:]
    tail = TAIL_RE.findall(rest)[0]
    dict_string = rest[0:-len(tail)]
    dict_string = dict_string.replace('=>', ':')
    # @todo Decompose line by line code and line comment
    dict_string = '{' + dict_string + '}'
    dictionary = eval(dict_string)
    return header, dictionary, tail


def compose_php_source(translation: (str, dict, str)) -> str:
    header, dictionary, tail = translation
    ret_str = header + '\n'
    for key, (original, translation, comment) in dictionary.items():
        translation = translation.replace("'", "\\'")
        ret_str += f"\t'{key}' => '{translation}',  // {original} | {comment}\n"
    ret_str += tail
    return ret_str

def translate_sentence(original:str, lang: str)-> str:
    # @todo Add translation
    return original[::-1]

def translate(decomposition: (str, dict, str), lang: str) -> list:
    header, dictionary, tail = decomposition
    result_dict = {}
    for key, original in dictionary.items():
        comment = COMMENT_RE.findall(original)
        if comment:
            print('comment', comment)
            comment = comment.stip('//')
        else:
            comment = ''
        result_dict[key] = (original, translate_sentence(original, lang), comment)
    return header, result_dict, tail

def for_one_file(in_filename: str, out_filname: str, lang: str):
    with open(in_filename, 'r') as f:
        source = f.read()
    decomposition = decompose_php_source(source)
    translation = translate(decomposition, lang)
    result = compose_php_source(translation)
    with open(out_filname, 'w') as f:
        f.write(result)

def for_all_files(in_dir: str, out_dir: str, lang: str, file_suffix: str = '.php'):
    print(in_dir)
    for root, dirs, files in sorted(os.walk(in_dir)):
        for file in sorted(files):
            if file.endswith(file_suffix):
                in_filename = os.path.join(root, file)
                out_filename = os.path.join(out_dir, lang, file)
                sys.stdout.write(f'{in_filename} ... ')
                sys.stdout.flush()
                for_one_file(in_filename=in_filename, out_filname=out_filename, lang=lang)
                sys.stdout.write(f'done.\n')
                sys.stdout.flush()
        break  # only one level

def main(in_dir: str, out_dir: str, lang: str):
    for_all_files(in_dir=in_dir, out_dir=out_dir, lang=lang)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__description__)

    default = IN_DIR
    parser.add_argument(
        '-id', '--in_dir',
        dest='in_dir',
        metavar='<in_dir>',
        type=str,
        required=False,
        default=default,
        help='Input directory (default:' + str(default) + ')'
    )

    default = OUT_DIR
    parser.add_argument(
        '-od', '--out_dir',
        dest='out_dir',
        metavar='<out_dir>',
        type=str,
        required=False,
        default=default,
        help='Output directory for result (default:' + str(default) + ')'
    )

    default = 'cs'
    lang_list = list(LANGUAGES.keys())
    parser.add_argument(
        '-l', '-language',
        dest='lang',
        metavar='<lang>',
        type=str,
        default=default,
        choices=lang_list,
        help=f'Languages (defaut="{default}", from {lang_list}')

    args = parser.parse_args()
    
    main(in_dir=args.in_dir, out_dir=args.out_dir, lang=args.lang)