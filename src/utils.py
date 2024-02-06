import logging

from bs4 import BeautifulSoup
from requests import RequestException
from exceptions import ParserFindTagException


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        raise


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        raise ParserFindTagException(error_msg)
    return searched_tag


def get_soup(session, url):
    try:
        response = get_response(session, url)
        if response is None:
            return
    except RequestException:
        raise

    return BeautifulSoup(response.text, features='lxml')


def write_logs(error_data, error_template):
    if not error_data:
        return

    for item in error_data:
        logging.warning(
            error_template.format(*item if type(item) == 'tuple' else item)
        )
