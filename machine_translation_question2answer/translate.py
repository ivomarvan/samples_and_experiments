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
from datetime import datetime
import translators as ts
from time import sleep
from pprint import pprint

# root of repository in your filesystem
THIS_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(THIS_FILE_DIR)

from languages import LANGUAGES

DATA_DIR = os.path.realpath(os.path.join(THIS_FILE_DIR, 'data'))
IN_DIR = os.path.join(DATA_DIR, 'orig')
OUT_DIR = os.path.join(DATA_DIR, 'outputs')

# Construction of regular expression
PREFIX_RE = r'\<\?php\n+'
SPACES = r'[\s]*'
HEADER_COMMENT_RE = r'/\*(?P<header_comment>[\d\D]*?)\*/'
ARRAY_HEADER = r'(?P<array_header>return array\(\n)'
KEY_RE = r'(?P<mark1>["\'])(?P<key>(?:(?=(?P<empty1>\\?))(?P=empty1).)*?)(?P=mark1)'
ARROW_RE = r'\s*=>\s*'
ORIG_RE = r'(?P<mark2>["\'])(?P<orig>(?:(?=(?P<empty2>\\?))(?P=empty2).)*?)(?P=mark2)'
COMMENT_RE = r'//(?P<comment>[^\n]*)'
ARRAY_LINE_RE = SPACES + KEY_RE + ARROW_RE + ORIG_RE + r'\s*,\s*' + r'(' + COMMENT_RE + r')?'

HEADER_RE = re.compile(PREFIX_RE + HEADER_COMMENT_RE + SPACES + ARRAY_HEADER)
ARRAY_LINE_RE = re.compile(ARRAY_LINE_RE)
# TAIL_RE = re.compile(r'(?P<array_tail>)\s*;\s*\)')
SEPARATOR_RE = re.compile(r'\s*\^[0-9]?\s*')

REP = 'https://github.com/ivomarvan/samples_and_experiments/machine_translation_question2answer'


def decompose_php_source(source: str) -> (re.match, dict, str):
    # take a header
    header_match = HEADER_RE.match(source)
    start, end = header_match.regs[0]
    rest = source[end:]
    lines = {}
    for line_match in ARRAY_LINE_RE.finditer(rest):
        if line_match:
            lines[line_match.group('key')] = (line_match.group('orig'), line_match.group('comment'))
    tail = rest[line_match.endpos:]
    return header_match, lines, tail

def compose_php_source(header_match: re.match, translated_lines: dict, tail: str, lang: str) -> str:
    ret_str = add_translation_message(header_match, lang)
    for key, (original, translation, comment) in translated_lines.items():
        translation = translation.replace("'", "\\'")
        ret_str += f"\t'{key}' => '{translation}',  // {original}"
        if not comment is None:
            ret_str += f'\t|\t{comment}'
        ret_str += '\n'
    ret_str += tail
    return ret_str

def add_translation_message(header_match: re.match, lang) -> str:
    tr_message = f'\n\tTranslated automatically by the software \n\t\t"{REP}"\n\t\t{datetime.now()}\n'
    tr_message += f'\t\tTo language: {lang} => {LANGUAGES[lang]}\n'
    _, end_of_header = header_match.regs[0]
    header_str = header_match.string
    start, end = header_match.regs[1]
    before = header_str[:start]
    content = header_str[start:end]
    after = header_str[end:end_of_header]
    return before + content + tr_message + after

def translate_sentence(original:str, lang: str)-> str:
    found_sep = False
    ret_str = ''
    last_end = 0
    for sep_match in SEPARATOR_RE.finditer(original):
        found_sep = True
        start, end = sep_match.regs[0]
        orig_part = original[last_end:start]
        ret_str += translate_part(orig_part, lang) + original[start:end]
        last_end = end
    if not found_sep:
        return translate_part(original, lang)
    else:
        if last_end < len(original):
            ret_str += translate_part(original[last_end:], lang)
        return ret_str

def translate_part(original: str, lang: str, translator = ts.google) -> str:
    # @todo CACHE TRANSLATION
    if original=='':
        return original
    sleep(0.2)
    return translator(original, from_language='en', to_language=lang)

def translate(lines: dict, lang: str) -> str:
    result_dict = {}
    for key, (orig, comment) in lines.items():
        result_dict[key] = (orig, translate_sentence(orig, lang), comment)
    return result_dict

def for_one_file(in_filename: str, out_filname: str, lang: str):
    with open(in_filename, 'r') as f:
        source = f.read()
    header_match, lines, tail = decompose_php_source(source)
    translated_lines = translate(lines=lines, lang=lang)
    result = compose_php_source(header_match=header_match, translated_lines=translated_lines, tail=tail, lang=lang)
    os.makedirs(os.path.dirname(out_filname), exist_ok=True)
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