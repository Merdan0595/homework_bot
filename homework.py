import os
import logging
import time
import sys


import requests
from http import HTTPStatus

import telegram

from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PAYLOAD = {'from_date': 1549962000}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='homework.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def check_tokens():
    """Проверить доступность переменных окружения."""
    if (PRACTICUM_TOKEN is None or TELEGRAM_TOKEN is None
       or TELEGRAM_CHAT_ID is None):
        logging.critical('Переменные окружения недоступны')
        sys.exit('Переменные окружения недоступны')


def send_message(bot, message):
    """Отправить сообщение в чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug('Сообщение успешно отправлено')
    except Exception as error:
        logging.error(error)
        raise (f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту, ответ с типом данных Python."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        logging.error('Сбой при запросе к эндпоинту')
        raise (f'Сбой при запросе к эндпоинту: {error}')
    if response.status_code == HTTPStatus.OK:
        response = response.json()
        return response
    else:
        logging.error('Сбой при запросе к эндпоинту')
        raise requests.RequestException


def check_response(response):
    """Проверить ответ на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не соответствующего типа данных')
    elif 'homeworks' not in response:
        logging.error('Отсутствуют ожидаемые ключи в ответе API')
        raise KeyError('Отсутсвует ключ "homeworks"')
    elif not isinstance(response["homeworks"], list):
        raise TypeError('Homeworks не соответствующего типа данных')
    return response['homeworks']


def parse_status(homework):
    """Извлечь информация о последней домашней работе."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']

        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError:
        logging.error('Неожиданный статус домашней работы')
        raise ('Недокументированный статус ДЗ либо работа без статуса')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    timestamp = timestamp - RETRY_PERIOD

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logging.debug('Статус не изменился')
            timestamp = response['current_date']
        except Exception as error:
            logging.error(error)
            message = f'Сбой в работе программы: {error}'
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
