import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import (CheckResponseException, GetApiException,
                        SendMessageException, StatusCodeException)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger()
streamHandler = logging.StreamHandler(sys.stdout)
logger.addHandler(streamHandler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ENV_CONST_DICT = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
}

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение {message} отправлено.')
    except SendMessageException as error:
        logger.error(f'Произошел сбой при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса возвращает ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except GetApiException:
        error_message = f'Не удалось подключиться по API {ENDPOINT}'
        logger.error(error_message)
        raise GetApiException(error_message)
    if response.status_code != HTTPStatus.OK:
        error_message = (
            f'Ошибка подключения к серверу Яндекс.Практикум'
            f' status code: {response.status_code}'
        )
        logger.error(error_message)
        raise StatusCodeException(
            f'Код отличный от 200: {response.status_code}'
        )
    response = response.json()
    keys = ['error', 'code']
    for key in keys:
        if key in response:
            error = response[key]
            error_message = (f'Ошибка ответа по API: {ENDPOINT} '
                             f'Описание {error}')
            logger.error(error_message)
            raise GetApiException(error_message)
    return response


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API, приведенный
    к типам данных Python.Если ответ API соответствует
    ожиданиям, то функция вернет список домашних работ.
    """
    if response == {}:
        error_message = 'Словарь значений пуст'
        logger.error(error_message)
        raise CheckResponseException(error_message)
    try:
        hw_list = response['homeworks']
    except KeyError:
        error_message = 'Ответ Api не содержит ключа homeworks'
        logger.error(error_message)
        raise CheckResponseException(error_message)
    if type(hw_list) != list:
        error_message = 'Ответ по ключу homeworks не является списком'
        logger.error(error_message)
        raise CheckResponseException(error_message)
    return hw_list


def parse_status(homework):
    """Извлекает из информации о конкретнойдомашней работе статус."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу homework_name {error}'
        logger.error(error_message)
        raise KeyError(error_message)
    try:
        homework_status = homework.get('status')
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу status {error}'
        logger.error(error_message)
        raise KeyError(error_message)
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        verdict = 'Ошибка в статуcе домашки'
        logger.error(verdict)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    функция вернет False, иначе — True.
    """
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        for key in ENV_CONST_DICT:
            if ENV_CONST_DICT[key] is None:
                logger.critical(
                    f'Отсутствует переменная окружения {key}'
                )
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    if not check_tokens():
        raise SystemExit()
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except GetApiException:
            error_message = 'Получен некорректный ответ по запросу к API'
            logger.error(error_message)
            send_message(bot, error_message)
            time.sleep(RETRY_TIME)
            continue
        try:
            homeworks = check_response(response)
            if homeworks[0].get('status') != status:
                status = homeworks[0].get('status')
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Статус проверки домашки не изменился')
            time.sleep(RETRY_TIME)
        except CheckResponseException as error:
            error_message = f'Некорректный ответ API {error}'
            logger.error(error_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
