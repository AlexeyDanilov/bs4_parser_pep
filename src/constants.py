from pathlib import Path

MAIN_DOC_URL = 'https://docs.python.org/3/'
PEP_DOC_URL = 'https://peps.python.org/'

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'parser.log'

DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
PRETTY = 'pretty'
FILE = 'file'

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}

ARCHIVE_DOWNLOAD = 'Архив был загружен и сохранён: {0}'
DATA_NOT_FOUND = 'Не удалось получить данные из {0}'
UNINSPECTED_STATUS = 'Несовпадающие статусы:{0}\n' \
                     'Статус в карточке: {1}\n' \
                     'Ожидаемые статусы: {2}'
