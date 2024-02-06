import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from requests import RequestException
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    MAIN_DOC_URL, PEP_DOC_URL, EXPECTED_STATUS, BASE_DIR, ARCHIVE_DOWNLOAD,
    DATA_NOT_FOUND, UNINSPECTED_STATUS
)
from outputs import control_output
from exceptions import TextNotFoundException
from utils import find_tag, get_soup, write_logs


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    sections_by_python = soup.select(
        '#what-s-new-in-python div.toctree-wrapper li.toctree-l1'
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор',)]
    request_errors = list()

    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        try:
            section_soup = get_soup(session, version_link)
            if section_soup is None:
                request_errors.append(version_link)
                continue
            results.append(
                (
                    version_link,
                    find_tag(section_soup, 'h1').text,
                    find_tag(section_soup, 'dl').text.replace('\n', ' '),)
            )

        except RequestException:
            request_errors.append(version_link)
            continue

    write_logs(request_errors, DATA_NOT_FOUND)

    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebar'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break

    else:
        raise TextNotFoundException('Ничего не нашлось')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in tqdm(a_tags):
        search = re.search(pattern, a_tag.text)
        if not search:
            version, status = a_tag.text, ''
        else:
            version, status = re.search(pattern, a_tag.text).groups()

        results.append((a_tag['href'], version, status))

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = get_soup(session, downloads_url)
    pdf_a4_link = soup.select_one(
        'table.docutils a[href$="pdf-a4.zip"]')['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    logging.info(ARCHIVE_DOWNLOAD.format(archive_path))


def pep(session):
    soup = get_soup(session, PEP_DOC_URL)
    section = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    tables = section.find_all('table', class_='pep-zero-table')
    abbrs = list()
    for table in tables:
        abbrs.extend(table.find_all('abbr'))

    count_status = defaultdict(int)
    request_errors = list()
    uninspected_statuses = list()
    for abbr in tqdm(abbrs):
        external_status = abbr.text[1:]
        external_status_decode = EXPECTED_STATUS.get(external_status)
        link = find_tag(abbr.find_next('td'), 'a')['href']
        url = urljoin(PEP_DOC_URL, link)
        try:
            interior_page = get_soup(session, url)
            interior_table = find_tag(
                interior_page, 'dl', attrs={'class': 'field-list'}
            )
        except RequestException:
            request_errors.append(url)
            continue

        for item in tqdm(interior_table.children):
            if 'Status' in item:
                interior_status = item.find_next_sibling().string
                count_status[interior_status] += 1
                if interior_status in external_status_decode:
                    continue

                uninspected_statuses.append(
                    (url, interior_status, *external_status_decode)
                )

        count_status['Total'] = len(abbrs)

    write_logs(uninspected_statuses, UNINSPECTED_STATUS)
    write_logs(request_errors, DATA_NOT_FOUND)

    return [count_status, count_status.values()]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    try:
        configure_logging()
        logging.info('Парсер запущен!')
        arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
        args = arg_parser.parse_args()
        logging.info(f'Аргументы командной строки: {args}')
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)

    except Exception as e:
        logging.warning(f'Возника проблема - {e}')

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
