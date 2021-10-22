from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request
import pymorphy2
import sqlite3
import nltk

import re

pymorph = pymorphy2.MorphAnalyzer()

db = SQLAlchemy()
app = Flask(__name__)

# Connect our base sqlite:///
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///insta_corpus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.app = app
db.init_app(app)


def tokenizer(text):
    return [i for i in nltk.word_tokenize(text) if i.isalpha()]


def lemmatizer(token):
    p = pymorph.parse(token)[0]
    return p.normal_form


def get_request_type(request):
    request_types = []
    request = request.split()
    list_of_pos = ['noun', 'adj', 'verb', 'infn',
                   'prtf', 'prts', 'grnd', 'numr',
                   'advb', 'npro', 'pred', 'prep',
                   'conj', 'prcl', 'intj']
    for item in request:
        item = item.lower()
        in_double_quotes = item.startswith('"') and item.endswith('"')
        in_single_quotes = item.startswith("'") and item.endswith("'")
        if item in list_of_pos:
            request_types.append((item, 'POS'))
        elif in_double_quotes or in_single_quotes:
            request_types.append((item, 'token'))
        elif re.search(r'^[а-яa-z0-9]+$', item):
            request_types.append((lemmatizer(item), 'lemma'))
        else:
            return 'Error, try again.'
    return request_types


def get_context_metadata_for_unigram(unigram_info):
    conn = sqlite3.connect('insta_corpus.db')
    cur = conn.cursor()

    item = unigram_info[0]

    in_double_quotes = item.startswith('"') and item.endswith('"')
    in_single_quotes = item.startswith("'") and item.endswith("'")
    if in_double_quotes or in_single_quotes:
        item = item[1:-1]

    tag = unigram_info[1]
    results = list(cur.execute(f'''SELECT id_morph, context, metadata 
        FROM morphology
        INNER JOIN context_metadata ON id_cm = context_id
        WHERE {tag} LIKE "{item}";'''))
    return results


def get_context_metadata_for_ngram(ngram_info):
    conn = sqlite3.connect('insta_corpus.db')
    cur = conn.cursor()

    all_contexts_and_metadata = []
    first_item_ids = get_context_metadata_for_unigram(ngram_info[0])
    for _id, context, metadata in first_item_ids:
        for i in range(_id + 1, _id + len(ngram_info)):
            item, tag = ngram_info[i - _id]

            in_double_quotes = item.startswith('"') and item.endswith('"')
            in_single_quotes = item.startswith("'") and item.endswith("'")
            if in_double_quotes or in_single_quotes:
                item = item[1:-1]

            if not list(cur.execute(f'''SELECT id_morph, context, metadata 
                                        FROM morphology
                                        INNER JOIN context_metadata  ON id_cm = context_id
                                        WHERE id_morph LIKE "{i}" AND {tag} LIKE "{item}";''')):
                break
        else:
            all_contexts_and_metadata.append([context, metadata])
    return all_contexts_and_metadata


@app.route("/")
def main_page():
    return render_template('main_page.html')


@app.route('/process', methods=['GET'])
def results():
    user_request = request.args.get('user_request')
    request_type = get_request_type(user_request)

    if len(request_type) == 1:
        results = get_context_metadata_for_unigram(request_type[0])
        results = [[i[1], i[2]] for i in results]
    elif len(request_type) > 1:
        results = get_context_metadata_for_ngram(request_type)
    else:
        return render_template('results.html', len_matches='0 🤷🏼‍♀️',
                               user_request=user_request)

    if results:
        return render_template('results.html', len_matches=f'{len(results)} 💁🏼‍♀️',
                               user_request=user_request, matches=results)
    return render_template('results.html', len_matches=f'{len(results)} 🤷🏼‍♀️️',
                           user_request=user_request)


if __name__ == "__main__":
    app.run(debug=True)
