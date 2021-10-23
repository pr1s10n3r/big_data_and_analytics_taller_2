import requests
import nltk

import logging
import re
import json
import datetime


from bs4 import BeautifulSoup
from header import Header


def build_header_text(object: dict) -> str:
    elements = object['content_elements']

    text = ''
    for element in elements:
        if element['type'] != 'text':
            continue

        text += element['content']

    return text


def build_header_from_json(category: str, object: dict) -> Header:
    item = Header()
    item.title = object['headlines']['basic']
    item.category = category
    item.datetime = datetime.datetime.strptime(
        object['created_date'], '%Y-%m-%dT%H:%M:%S.%fZ')
    canonical_url = object['canonical_url']
    item.url = f'https://www.elespectador.com{canonical_url}'

    item.text = build_header_text(object)

    return item


def extract_page_headers(category: str, html: str) -> list:
    soup = BeautifulSoup(html, 'html.parser')
    metadata = soup.find('script', attrs={'id': 'fusion-metadata'})

    page_content = re.search(r'\{\"(.*)\"\}\;', metadata.get_text())
    if not page_content:
        return None

    raw_json = page_content.group(0)
    raw_json = raw_json[:-1]
    parsed_json = json.loads(raw_json)

    headers = []

    elements = parsed_json['content_elements']
    for elem in elements:
        header = build_header_from_json(category, elem)
        headers.append(header)

    return headers


def get_category_news(category_name: str, pages: int) -> tuple:
    news = (category_name, [])

    while pages > 0:
        url = f'https://www.elespectador.com/archivo/{category_name}/{pages}'
        logging.info(f'[category:{category_name}] getting news from {url}')

        resp = requests.get(url)
        if resp.status_code != 200:
            logging.error(
                f'[status_code:{resp.status_code}][url:{url}] unable to get page')

        headers = extract_page_headers(category_name, resp.text)
        for header in headers:
            news[1].append(header)

        pages -= 1

    return news


def insert_into_database(category_news: tuple):
    from pymongo import MongoClient
    from os import getenv
    from sys import exit

    password = getenv('MONGO_PASSWORD')
    if password is None:
        logging.error('*-----------------------------------------*')
        logging.error('| MONGO_PASSWORD env variable was not set |')
        logging.error('*-----------------------------------------*')
        exit(1)
    else:
        import urllib
        password = urllib.parse.quote_plus(password)

    client = MongoClient(f'mongodb+srv://news_database:{password}@cluster0.efobz.mongodb.net/myFirstDatabase?retryWrites=true&w=majority')

    db = client.news_database
    news = db.news

    for cn in category_news[1]:
        new_id = news.insert_one(cn.__dict__).inserted_id
        logging.info(f'[id:{new_id}] was inserted')


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    """
    ┌────────────────────────────┐
    │                            │
    │        PRIMER PUNTO        │
    │                            │
    └────────────────────────────┘
    """
    categories = ['colombia', 'salud', 'economia', 'ciencia', 'tecnologia']
    local_category_news = []
    for category in categories:
        category_news = get_category_news(category, 5)
        local_category_news.append(category_news)
        insert_into_database(category_news)

    """
    ┌────────────────────────────┐
    │                            │
    │        SEGUNDO PUNTO       │
    │                            │
    └────────────────────────────┘
    """
    nltk.download('popular')

    text = ''
    for cn in local_category_news:
        news = cn[1]

        for new in news:
            text += new.title + ' '
            text += new.text + ' '
    
    text = text.lower()
    
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords

    stop_words = set(stopwords.words('spanish'))
    words = word_tokenize(text)
    # Remueve caracteres especiales
    words = [word.lower() for word in words if word.isalpha()]

    filtered_words = []
    special = ['http', 'https', 'b', 'html', 'a', 'i']

    for w in words:
        if w not in stop_words and w not in special:
            filtered_words.append(w)

    frec_dist = nltk.FreqDist(filtered_words)
    common_words = frec_dist.most_common(20)

    cw_str = ''
    for cw in common_words:
        cw_str += cw[0] + ' '

    import matplotlib.pyplot as plt
    from wordcloud import WordCloud

    wordcloud = WordCloud(max_font_size=50, max_words=20, background_color='white').generate(cw_str)
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.show()