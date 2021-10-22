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
    client = MongoClient('localhost', 27017)

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
    for category in categories:
        category_news = get_category_news(category, 5)
        insert_into_database(category_news)

    """
    ┌────────────────────────────┐
    │                            │
    │        SEGUNDO PUNTO       │
    │                            │
    └────────────────────────────┘
    """
    nltk.download('popular')
