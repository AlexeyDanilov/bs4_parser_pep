import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import MAIN_DOC_URL, PEP_DOC_URL, EXPECTED_STATUS, BASE_DIR
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор',)]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'h1')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1, dl_text,)
        )

    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebar'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break

    else:
        raise Exception('Ничего не нашлось')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        search = re.search(pattern, a_tag.text)
        if not search:
            version, status = a_tag.text, ''
        else:
            version, status = re.search(pattern, a_tag.text).groups()

        results.append((link, version, status))

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    table_tag = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag, 'a', {'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    response = get_response(session, PEP_DOC_URL)
    soup = BeautifulSoup(response.text, features='lxml')
    section_1 = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    section_2 = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    section_3 = find_tag(soup, 'section', attrs={'id': 'reserved-pep-numbers'})
    tables = list()
    for section in (section_1, section_2, section_3,):
        tables.extend(
            section.find_all('table', class_='pep-zero-table')
        )

    trs = list()
    for table in tables:
        tbodies = table.find_all('tbody')
        for tbody in tbodies:
            trs_tag = tbody.find_all('tr')
            trs.extend(trs_tag)

    count_status = {
        'Active': 0,
        'Accepted': 0,
        'Deferred': 0,
        'Final': 0,
        'Provisional': 0,
        'Rejected': 0,
        'Superseded': 0,
        'Withdrawn': 0,
        'Draft': 0,
        'April Fool!': 0,
        'Total': len(trs)
    }

    for tr in trs:
        td = find_tag(tr, 'td')
        external_status = td.text[1:]
        external_status_decode = EXPECTED_STATUS.get(external_status)
        link = find_tag(td.find_next_sibling('td'), 'a')['href']
        url = urljoin(PEP_DOC_URL, link)
        resp = get_response(session, url)
        interior_page = BeautifulSoup(resp.text)
        interior_table = find_tag(
            interior_page, 'dl', attrs={'class': 'field-list'}
        )
        for item in interior_table.children:
            if 'Status' in item:
                interior_status = item.find_next_sibling().string
                count_status[interior_status] += 1
                if interior_status in external_status_decode:
                    continue

                logging.warning(
                    f'''
                        Несовпадающие статусы:
                        {url}
                        Статус в карточке: {interior_status}
                        Ожидаемые статусы: {external_status_decode}
                    '''
                )

    return [count_status, count_status.values()]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
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

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
