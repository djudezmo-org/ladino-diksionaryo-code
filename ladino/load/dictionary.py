import copy
import json
import logging
import os
import re
import yaml

from ladino.common import LadinoError, languages, words_to_url

VALID_FIELDS_IN_WORD_FILES = set(['conjugations', 'grammar', 'versions', 'id', 'orijen', 'kategorias', 'linguas', 'comments'])
class Dictionary():
    def __init__(self, config):
        self.yaml_files = []  # each entry as loaded from the yaml files of words
        self.words = [] # list of dictionaries. Each "version" of each word has one entry in this.
                        # A ladino word might appear more than once as the same word might have different
                        # meanings in different contexts. (and different grammatical role)

        self.all_examples = []
        self.lists = {lst:[] for lst in config['listas'] }
        self.categories = {cat:[] for cat in config['kategorias'] }
        self.gramer = {name:[] for name in config['gramatika'] }
        self.orijenes = {name:[] for name in config['orijenes'] }
        self.languages = {name:[] for name in config['linguas'] }

        self.count = {}
        self.word_mapping = {}
        self.pages = {}

        self.count['dictionary'] = {}
        self.word_mapping['accented'] = {}
        for language in ['ladino'] + languages:
            self.count['dictionary'][language] = {
                'words': 0,
                'examples': 0,
            }
            self.word_mapping[language] = {}
            self.pages[language] = {}

def load_config(path_to_repo):
    config_file = os.path.join(path_to_repo, 'config.yaml')
    with open(config_file) as fh:
        config = yaml.safe_load(fh)
    for field in ['linguas', 'kategorias', 'orijenes', 'gramatika', 'gender', 'numero', 'pajinas', 'listas', 'tiempos', 'pronombres', 'verbos-iregolares']:
        if field not in config:
            raise LadinoError(f"Field '{field}' is missing from config file '{config_file}'")
    return config

def check_and_collect_grammar(config, data, dictionary, filename):
    invalid_fields =  set(data.keys()) - VALID_FIELDS_IN_WORD_FILES
    if invalid_fields:
        raise LadinoError(f"Invalid fields '{invalid_fields}' found in '{filename}'")

    if 'grammar' not in data:
        raise LadinoError(f"The 'grammar' field is missing from file '{filename}'")

    grammar = data['grammar']

    if grammar not in config['gramatika']:
        raise LadinoError(f"Invalid grammar '{grammar}' in file '{filename}'")

    if grammar == 'verb' and 'conjugations' not in data:
        raise LadinoError(f"Grammar is 'verb', but there is NO 'conjugations' field in '{filename}'")
    if grammar != 'verb' and 'conjugations' in data:
        raise LadinoError(f"Grammar is NOT a 'verb', but there are conjugations in '{filename}'")

    for version in data.get('versions', []):
        gender = version.get('gender')
        # print(gender)
        if grammar in ['noun', 'pronoun']:
            if gender is None:
                raise LadinoError(f"The 'gender' field is None in '{filename}' version {version}")
            if gender not in config['gender']:
                raise LadinoError(f"Invalid value '{gender}' in 'gender' field in '{filename}' version {version}")
            number = version.get('number')
            if number is None:
                raise LadinoError(f"The 'number' field is None in '{filename}' version {version}")
            if number not in config['numero']:
                raise LadinoError(f"The 'number' field is '{number}' in '{filename}' version {version}")
        elif grammar in ['adjective']:
            pass # TODO some adjectives have this, some don't?
        else:
            pass # TODO
        #     if gender is not None:
        #         raise LadinoError(f"Unnecessary 'gender' field in '{filename}' version {version}")

    dictionary.gramer[grammar].append(data)


def check_and_collect_orijen(config, data, dictionary, filename):
    if 'orijen' not in data:
        raise LadinoError(f"The 'orijen' field is missing from file '{filename}'")
    orijen  = data['orijen']
    if orijen not in config['orijenes']:
        raise LadinoError(f"Invalid orijen '{orijen}' in file '{filename}'")

    dictionary.orijenes[orijen].append(data)

    return orijen

def check_and_collect_languages(config, data, dictionary, filename):
    if 'linguas' not in data:
        return []
    logging.info(f"check_and_collect_languages(config, data, dictionary, {filename})")
    languages = data['linguas']
    for language in languages:
        if language not in config['linguas']:
            raise LadinoError(f"Invalid value in linguas field: '{language}'. Valid values are {config['linguas']} in file '{filename}'")

    dictionary.languages[language].append(data)

    return languages


def check_and_collect_categories(config, data, dictionary, filename):
    if 'kategorias' not in data:
        return
    for cat in data['kategorias']:
        if cat not in config['kategorias']:
            raise LadinoError(f"Invalid category '{cat}' in file '{filename}'")
        dictionary.categories[cat].append(data)

def make_them_list(translations, filename):
    for language in languages:
        if language not in translations:
            continue
        translations[language] = make_it_list(translations, language, filename)

def make_it_list(translations, language, filename):
    target_words = translations[language]
    if target_words.__class__.__name__ == 'str':
        if target_words == '':
            return []
        else:
            return [target_words]
    elif target_words.__class__.__name__ == 'list':
        return target_words
    else:
        raise LadinoError(f"bad type {target_words.__class__.__name__} for {language} in {translations} in '{filename}'")

def check_and_collect_lists(config, data, dictionary):
    for lst, listed_words in config['listas'].items():
        #print(data['versions'][0]['ladino'])
        #print(listed_words)
        if 'versions' in data and 'ladino' in data['versions'][0] and data['versions'][0]['ladino'] in listed_words:
            dictionary.lists[lst].append(data)
        # TODO: include also words from the lists that don't appear in our dictionaries (without a link)
        # TODO: add these words to the list of missing words


def load_dictionary(config, limit, path_to_dictionary):
    logging.info(f"Path to dictionary: '{path_to_dictionary}'")
    dictionary = Dictionary(config)

    irregulars = config['verbos-iregolares']
    count = 0

    files = os.listdir(path_to_dictionary)
    for filename in files:
        if re.search(r'^\.[a-z_ -]+\.yaml\.swp$', filename):
            continue
        if not re.search(r'^[a-z_ -]+\.yaml$', filename):
            raise LadinoError(f"Invalid filename '{filename}'")

        count += 1
        if limit is not None and count > limit:
            break

        path = os.path.join(path_to_dictionary, filename)
        logging.info(path)
        with open(path) as fh:
            data = yaml.safe_load(fh)

        dictionary.yaml_files.append(data)

        check_and_collect_grammar(config, data, dictionary, filename)
        orijen = check_and_collect_orijen(config, data, dictionary, filename)
        languages = check_and_collect_languages(config, data, dictionary, filename)
        check_and_collect_categories(config, data, dictionary, filename)
        check_and_collect_lists(config, data, dictionary)

        if 'versions' not in data:
            raise LadinoError(f"The 'versions' field is missing from file '{filename}'")

        comments = data.get('comments')
        if comments == []:
            comments = None

        for version in data['versions']:
            if 'ladino' not in version:
                raise LadinoError(f"The ladino 'version' is missing from file '{filename}'")

            if version['ladino'].strip() == '':
                raise LadinoError(f"The ladino 'version' is empty in file '{filename}'")

            if 'accented' in version and version['accented'] == version['ladino']:
                print(f"The accented is the same as the ladino in '{filename}'")
                #raise LadinoError(f"The accented is the same as the ladino in '{filename}'")

            version['source'] = filename

            if 'translations' in version:
                make_them_list(version['translations'], filename)

            if comments is not None:
                version['comments'] = comments
                comments = None
            version['orijen'] = orijen
            version['languages'] = languages
            dictionary.words.append(version)

        conjugations = config['tiempos']
        pronouns = config['pronombres']
        if 'conjugations' in data:
            add_conjugation(data, irregulars)
            for verb_time, conjugation in data['conjugations'].items():
                if verb_time not in conjugations:
                    raise LadinoError(f"Verb conjugation time '{verb_time}' is no recogrnized in '{filename}'")
                #print(conjugation)
                for pronoun, version in conjugation.items():
                    if pronoun not in pronouns:
                        raise LadinoError(f"Incorrect pronoun '{pronoun}' in verb time '{verb_time}' in '{filename}'")
                    if 'ladino' not in version:
                        raise LadinoError(f"The field 'ladino' is missing from verb time: '{verb_time}' pronoun '{pronoun}' in file '{filename}'")
                    version['source'] = filename
                    if 'translations' in version:
                        make_them_list(version['translations'], filename)
                    dictionary.words.append(version)

    #print(dictionary.words)
    #print(dictionary.all_examples[0])
    for cat in dictionary.categories.keys():
        dictionary.categories[cat].sort(key=lambda word: (word['versions'][0]['ladino'], word['versions'][0]['translations']['inglez']))
    for field in dictionary.orijenes.keys():
        dictionary.orijenes[field].sort(key=lambda word: (word['versions'][0]['ladino'], word['versions'][0]['translations']['inglez']))
    for lst in dictionary.lists.keys():
        lookup = {word:ix for ix, word in enumerate(config['listas'][lst])}
        dictionary.lists[lst].sort(key=lambda word: lookup[word['versions'][0]['ladino']])

    collect_data(dictionary)

    return dictionary

def add_conjugation(verb, irregulars):
    return;
    ladino = verb['versions'][0]['ladino']
    #verb['conjugations']['infinito'] = verb['versions'][0]['ladino'],
    if ladino not in irregulars:
        root = ladino[0:-2]

        if ladino.endswith('ar'):
            if 'prezente' not in verb['conjugations']:
                verb['conjugations']['prezente'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'o' },
                    'tu':       { 'translations': {}, 'ladino': root + 'as' },
                    'el':       { 'translations': {}, 'ladino': root + 'a' },
                    'mozotros': { 'translations': {}, 'ladino': root + 'amos' },
                    'vozotros': { 'translations': {}, 'ladino': root + 'ash' }, # ásh
                    'eyos':     { 'translations': {}, 'ladino': root + 'an' },
                }
            if 'imperfekto' not in verb['conjugations']:
                verb['conjugations']['imperfekto'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'ava' },
                    'tu':       { 'translations': {}, 'ladino': root + 'avas' },
                    'el':       { 'translations': {}, 'ladino': root + 'ava' },
                    'mozotros': { 'translations': {}, 'ladino': root + 'avamos' }, # ávamos
                    'vozotros': { 'translations': {}, 'ladino': root + 'avash' },
                    'eyos':     { 'translations': {}, 'ladino': root + 'avan' },
                }
            if 'pasado' not in verb['conjugations']:
                verb['conjugations']['pasado'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'i' },   # í
                    'tu':       { 'translations': {}, 'ladino': root + 'ates' },
                    'el':       { 'translations': {}, 'ladino': root + 'o' },  # ó
                    'mozotros': { 'translations': {}, 'ladino': root + 'imos' },
                    'vozotros': { 'translations': {}, 'ladino': root + 'atesh' },
                    'eyos':     { 'translations': {}, 'ladino': root + 'aron' },
                }

        if ladino.endswith('er'):
            if 'prezente' not in verb['conjugations']:
                verb['conjugations']['prezente'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'o' },
                    'tu':       { 'translations': {}, 'ladino': root + 'es' },
                    'el':       { 'translations': {}, 'ladino': root + 'e' },
                    'mozotros': { 'translations': {}, 'ladino': root + 'emos' },
                    'vozotros': { 'translations': {}, 'ladino': root + 'esh' }, # ésh
                    'eyos':     { 'translations': {}, 'ladino': root + 'en' },
                }
            if 'imperfekto' not in verb['conjugations']:
                verb['conjugations']['imperfekto'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'ia' },    # ía
                    'tu':       { 'translations': {}, 'ladino': root + 'ias' },   # ías
                    'el':       { 'translations': {}, 'ladino': root + 'ia' },    # ía
                    'mozotros': { 'translations': {}, 'ladino': root + 'iamos' }, # íamos
                    'vozotros': { 'translations': {}, 'ladino': root + 'iash' },  # íash
                    'eyos':     { 'translations': {}, 'ladino': root + 'ian' },   # ían
                }
            if 'pasado' not in verb['conjugations']:
                verb['conjugations']['pasado'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'i' },   # í
                    'tu':       { 'translations': {}, 'ladino': root + 'ites' },
                    'el':       { 'translations': {}, 'ladino': root + 'io' },  # ió
                    'mozotros': { 'translations': {}, 'ladino': root + 'imos' },
                    'vozotros': { 'translations': {}, 'ladino': root + 'itesh' },
                    'eyos':     { 'translations': {}, 'ladino': root + 'ieron' },
                }

        if ladino.endswith('ir'):
            if 'prezente' not in verb['conjugations']:
                verb['conjugations']['prezente'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'o' },
                    'tu':       { 'translations': {}, 'ladino': root + 'es' },
                    'el':       { 'translations': {}, 'ladino': root + 'e' },
                    'mozotros': { 'translations': {}, 'ladino': root + 'imos' },
                    'vozotros': { 'translations': {}, 'ladino': root + 'ish' }, # ísh
                    'eyos':     { 'translations': {}, 'ladino': root + 'en' },
                }
            if 'imperfekto' not in verb['conjugations']:
                verb['conjugations']['imperfekto'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'ia' },    # ía
                    'tu':       { 'translations': {}, 'ladino': root + 'ias' },   # ías
                    'el':       { 'translations': {}, 'ladino': root + 'ia' },    # ía
                    'mozotros': { 'translations': {}, 'ladino': root + 'iamos' }, # íamos
                    'vozotros': { 'translations': {}, 'ladino': root + 'iash' },  # íash
                    'eyos':     { 'translations': {}, 'ladino': root + 'ian' },   # ían
                }
            if 'pasado' not in verb['conjugations']:
                verb['conjugations']['pasado'] = {
                    'yo':       { 'translations': {}, 'ladino': root + 'i' },   # í
                    'tu':       { 'translations': {}, 'ladino': root + 'ites' },
                    'el':       { 'translations': {}, 'ladino': root + 'io' },  # ió
                    'mozotros': { 'translations': {}, 'ladino': root + 'imos' },
                    'vozotros': { 'translations': {}, 'ladino': root + 'itesh' },
                    'eyos':     { 'translations': {}, 'ladino': root + 'ieron' },
                }



def add_word(word_mapping, source_language, target_language, source_word, target_words):
    if target_language not in word_mapping[source_language][source_word]:
        word_mapping[source_language][source_word][target_language] = []
    word_mapping[source_language][source_word][target_language].extend(target_words)
    word_mapping[source_language][source_word][target_language] = sorted(set(word_mapping[source_language][source_word][target_language]))

def add_ladino_word(original_word, accented_word, entry, dictionary):
    word = original_word.lower()
    logging.info(f"Add ladino word: '{original_word}' '{word}' '{accented_word}'")
    #print(entry)
    dictionary.count['dictionary']['ladino']['words'] += 1

    source_language = 'ladino'

    if 'accented' in entry:
        accented = entry["accented"]
        #print(entry)
        if accented not in dictionary.word_mapping['accented']:
            dictionary.word_mapping['accented'][accented] = []
            dictionary.word_mapping['accented'][accented].append(entry)

    if word not in dictionary.word_mapping[source_language]:
        dictionary.word_mapping[source_language][word] = {}
    for target_language, target_words in entry['translations'].items():
        add_word(dictionary.word_mapping, source_language, target_language, word, target_words)
    add_word(dictionary.word_mapping, source_language, 'ladino', word, [original_word])

    if word not in dictionary.pages[source_language]:
        dictionary.pages[source_language][word] = []
    dictionary.pages[source_language][word].append(entry)
    dictionary.pages[source_language][word].sort(key=lambda x: (x['ladino'], x['translations']['inglez'][0] if x['translations'].get('inglez') else ''))

    if accented_word and accented_word != word:
        add_word(dictionary.word_mapping, source_language, target_language='accented', source_word=word, target_words=[accented_word])

def add_translated_words(source_language, entry, dictionary):
    translations = entry['translations'].get(source_language)
    #print(f"{source_language}: {translations}")
    if translations is None:
        return

    for word in translations:
        word = word.lower()
        if word not in dictionary.word_mapping[source_language]:
            dictionary.word_mapping[source_language][word] = []
        dictionary.word_mapping[source_language][word].append(entry['ladino'])
        dictionary.word_mapping[source_language][word] = sorted(set(dictionary.word_mapping[source_language][word]))
        dictionary.count['dictionary'][source_language]['words'] += 1

        if word not in dictionary.pages[source_language]:
            dictionary.pages[source_language][word] = []
        dictionary.pages[source_language][word].append(entry)
        dictionary.pages[source_language][word].sort(key=lambda x: len(json.dumps(x, sort_keys=True)))



def collect_data(dictionary):
    logging.info("Collect more data")

    for entry in dictionary.words:
        add_ladino_word(entry['ladino'], entry.get('accented'), entry, dictionary)

        if 'alternative-spelling' in entry:
            for alt_entry in entry['alternative-spelling']:
                entry_copy = copy.deepcopy(entry)
                alt_entries =  entry_copy.pop('alternative-spelling')

                new_alt = {}
                fields = ['ladino', 'accented', 'audio']
                for field in fields:
                    if field in entry_copy:
                        new_alt[field] =  entry_copy.pop(field)
                    if field in alt_entry:
                        entry_copy[field] = alt_entry[field]
                alt_entries.append(new_alt)

                entry_copy['alternative-spelling'] = list(filter(lambda xyz: xyz['ladino'] != alt_entry['ladino'], alt_entries))

                #if 'examples' in entry_copy:
                #    entry_copy['examples'] = list(filter(lambda xyz: alt_entry['ladino'] in xyz['ladino'], entry['examples']))
                add_ladino_word(alt_entry['ladino'], alt_entry.get('accented'), entry_copy, dictionary)

        for language in languages:
            add_translated_words(language, entry, dictionary)


