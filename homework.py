import os
import logging
import time
import sys
from http import HTTPStatus

import requests
import telegram

from dotenv import load_dotenv
from exceptions import (SendMessageFailException,
                        HomeworkOrTimestampException, HTTPStatusNotOKException)


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

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='homework.log',
        format=('%(asctime)s - %(levelname)s '
                '- %(message)s - %(funcName)s - %(lineno)d')
    )


def check_tokens():
    """Проверить доступность переменных окружения."""
    logging.info('Начало проверки доступности переменных окружения')
    tokens = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    if tokens is False:
        logging.critical('Переменные окружения недоступны')
        sys.exit('Переменные окружения недоступны')


def send_message(bot, message):
    """Отправить сообщение в чат."""
    logging.info('Отправление сообщения в чат')
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        raise SendMessageFailException(
            f'Ошибка при отправке сообщения: {error}'
        )
    logging.debug('Сообщение успешно отправлено')


def get_api_answer(timestamp):
    """Запрос к эндпоинту, ответ с типом данных Python."""
    logging.info('Запрос к эндпоинту')
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise HomeworkOrTimestampException(
            f'Сбой при запросе к эндпоинту: {error}'
        )
    if response.status_code == HTTPStatus.OK:
        response = response.json()
        return response
    else:
        raise HTTPStatusNotOKException(
            f'Ошибка! Код ответа сервера: {response.status_code}'
        )


def check_response(response):
    """Проверить ответ на соответствие документации."""
    logging.info('Проверка ответа API на соответствие')
    if not isinstance(response, dict):
        raise TypeError('Ответ не соответствующего типа данных')
    if 'homeworks' not in response:
        raise KeyError('Отсутсвует ключ "homeworks"')
    if not isinstance(response["homeworks"], list):
        raise TypeError('Homeworks не соответствующего типа данных')
    return response['homeworks']


def parse_status(homework):
    """Извлечь информация о последней домашней работе."""
    logging.info('Получение информации о последней домашней работе')

    homework_status = homework['status']

    if 'homework_name' not in homework:
        raise HomeworkOrTimestampException(
            'Недокументированный статус ДЗ, либо работа без статуса'
        )
    if not HOMEWORK_VERDICTS.get(homework_status):
        raise HomeworkOrTimestampException(
            'Недокументированный статус ДЗ, либо работа без статуса'
        )
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework_status]
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
