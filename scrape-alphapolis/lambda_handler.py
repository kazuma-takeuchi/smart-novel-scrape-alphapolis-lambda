import os
import re
import json
import time
import base64
import requests
import logging
from urllib.request import urlopen

from datetime import datetime
from bs4 import BeautifulSoup
from datetime import datetime

from models import DEFAULT_DOCUMENT

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SITE_NAME = os.getenv('SITE_NAME')
BASE_URL = os.getenv('BASE_URL')


def get_html(url):
    res = requests.get(url)
    if res.status_code == 200:
        return res.content
    else:
        return None

        
def create_id(url):
    id_ = SITE_NAME + "-" + url.split('/')[-1]
    return id_

def jst_str2ts_epoch_milli(jst, format="%Y-%m-%d %H:%M:%S"):
    dt = datetime.strptime(jst + "+0900", format + "%z")
    ts = dt.timestamp() * 1000
    return ts

def extract_attributes(html):
    document = DEFAULT_DOCUMENT
    soup = BeautifulSoup(html, "html.parser")
    document['title'] = soup.find("h2", class_="title").get_text().strip()
    document['author'] = soup.find("div", class_="author").findAll("a")[0].get_text().strip()
    document['genre'] = soup.find("span", class_="subcategory").find("a", class_="content-status novels").get_text().strip()
    document['tag'] = [t.get_text().strip() for t in soup.find_all("span", class_="tag")]
    document['description'] = soup.find("div", class_="abstract").get_text().strip()
    table = soup.findAll("table", class_="detail")[0]
    rows = table.findAll("tr")
    for i, row in enumerate(rows):
        text_th = row.find("th").get_text()
        if text_th == 'お気に入り':
            document['like_count'] = int(re.sub(r'\D', '', row.find("td").get_text()).strip())
        if text_th == '初回公開日時':
            document['created_at'] = jst_str2ts_epoch_milli(row.find("td").get_text(), format="%Y.%m.%d %H:%M")
        if text_th == '更新日時':
            document['updated_time'] = jst_str2ts_epoch_milli(row.find("td").get_text(), format="%Y.%m.%d %H:%M")
        if text_th == '文字数':
            document['length'] = int(re.sub(r'\D', '', row.find("td").get_text()).strip())
            break
    return document

def lambda_handler(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    logger.info(event)
    logger.info(f'event {event}')
    logger.info(f'BASE_URL = {BASE_URL}')
    url = BASE_URL + event['url']
    logger.info(f'scrape {url}')
    logger.info('BEGIN scraping')
    html = get_html(url)
    html = html.decode("utf-8")
    logger.info('END scraping')
    document = extract_attributes(html)
    id_ = create_id(url)
    document['key'] = id_
    document['url'] = url
    document['site_name'] = SITE_NAME
    res = {
        "document": document,
        "id": id_
        }
    return res