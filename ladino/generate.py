#!/usr/bin/env python

import argparse
import collections
import logging
import os
import sys
import datetime
import re
from yaml import safe_load

import ladino.common
from ladino.load.dictionary import load_dictionary, load_config, Dictionary
from ladino.load.examples import load_examples
from ladino.export import generate_main_page, export_to_html, create_sitemap

ladino.common.start = datetime.datetime.now().replace(microsecond=0)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dictionary", help="path to directory where we find the dictionary files",
    )
    parser.add_argument(
        "--html", help="path to directory where to generate html files",
    )
    parser.add_argument(
        "--whatsapp", help="path to whatsapp files",
    )
    parser.add_argument(
        "--unafraza", help="path to una fraza files",
    )
    parser.add_argument(
        "--sounds", help="path to sounds repository",
    )
    parser.add_argument(
        "--pages", help="path to fixed pages repository",
    )
    parser.add_argument("--ladinadores", help="path to Ladinadores repository")
    parser.add_argument("--enkontros", help="path to Enkontros de Alhad repository")
    parser.add_argument(
        "--books", help="pathes to repository of a book", nargs="+",
    )
    action = parser.add_mutually_exclusive_group(required=False)
    action.add_argument("--main", action='store_true', help="Create the main page only")
    action.add_argument("--all",  action='store_true', help="Create all the pages")

    parser.add_argument("--log", action="store_true", help="Additional logging")
    parser.add_argument("--pretty", action="store_true", help="Pretty save json files")
    parser.add_argument("--limit", type=int, help="Limit number of words")

    args = parser.parse_args()

    if args.all and not args.dictionary:
        print("\n* If --all is provided we also need --directory\n")
        parser.print_help()
        exit(1)

    if (args.main or args.all) and not args.html:
        print("\n* If either --main or --all are provided we also need --html\n")
        parser.print_help()
        exit(1)

    return args

def process_examples(dictionary, examples):
    # logging.info(f"examples: {examples}")
    # logging.info(f"dictionary.words: {dictionary.words}")
    words = set( word['ladino'] for word in dictionary.words )
    logging.info(f"words: {words}")
    word_to_examples = { word:[] for word in words }
    logging.info(f"word_to_examples: {word_to_examples}")
    for example in examples:
        # logging.info(f'example: {example}')
        # logging.info(f"example.ladino: {example['ladino']}")

        unique_words_in_example = set(re.sub(r'[.,;!?:]', ' ', example['ladino']).lower().split())
        for word in unique_words_in_example:
            # logging.info(f"example word: {word}")
            if word in words:
                word_to_examples[word].append(example)
    #print(dictionary.word_mapping['ladino'])
    return word_to_examples

def main():
    args = get_args()
    if args.log:
        logging.basicConfig(level=logging.INFO)
    logging.info("Start generating Ladino dictionary website")

    if args.main:
        generate_main_page(args.html)

    if args.dictionary:
        path_to_repo = args.dictionary
        config = load_config(path_to_repo)

        dictionary = load_dictionary(config, args.limit, os.path.join(path_to_repo, 'words'))
        logging.info(f'dictionary.count: {dictionary.count}')
        # logging.info(f'dictionary.words: {dictionary.words}')

        examples = load_examples(os.path.join(path_to_repo, 'examples'))
        word_to_examples = process_examples(dictionary, examples)
        for example in examples:
            if 'ladino' not in example:
                raise Exception("Ladino is missing from example")
            dictionary.count['dictionary']['ladino']['examples'] += 1
            for language in ladino.common.languages:
                if language in example:
                    dictionary.count['dictionary'][language]['examples'] += 1

    sound_people = {}
    if args.sounds:
        with open(os.path.join(args.sounds, 'people.yaml')) as fh:
            sound_people = safe_load(fh)

    if args.all:
        export_to_html(config, dictionary, examples, word_to_examples, sound_people, path_to_repo, args.html, whatsapp_dir=args.whatsapp, unafraza=args.unafraza, pages=args.pages, books=args.books, ladinadores=args.ladinadores, enkontros=args.enkontros, pretty=args.pretty)
        create_sitemap(args.html)


    end = datetime.datetime.now().replace(microsecond=0)
    logging.info(f"Elapsed time: {(end-ladino.common.start).total_seconds()} sec")


if __name__ == "__main__":
    main()
