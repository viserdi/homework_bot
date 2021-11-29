import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

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

RETRY_TIME = 10
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
        logging.info(f'Сообщение {message} отправлено.')
    except SendMessageException as error:
        logging.error(f'Произошел сбой при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса возвращает ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if response.status_code != 200:
        error_message = (
            f'Ошибка подключения к серверу Яндекс.Практикум'
            f' status code: {response.status_code}'
        )
        logging.error(error_message)
        raise StatusCodeException(
            f'Код отличный от 200: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность. В качестве параметра функция
    получает ответ API, приведенный к типам данных Python.
    Если ответ API соответствует ожиданиям,
    то функция вернет список домашних работ.
    """
    if response == {}:
        error_message = 'Словарь значений пуст'
        logging.error(error_message)
        raise Exception(error_message)
    hw_list = response['homeworks']
    if hw_list is None:
        error_message = 'Ответ Api не содержит ключа homeworks'
        logging.error(error_message)
        raise Exception(error_message)
    if type(hw_list) != list:
        error_message = 'Ответ по ключу homeworks не является списком'
        logging.error(error_message)
        raise Exception(error_message)
    return hw_list


def parse_status(homework):
    """Извлекает из информации о конкретной домашней
    работе статус этой работы.
    """
    try:
        homework_name = homework.get('homework_name')
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу homework_name {error}'
        logging.error(error_message)
        return error_message
    try:
        homework_status = homework.get('status')
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу status {error}'
        logging.error(error_message)
        return error_message
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        verdict = 'Ошибка в статуcе домашки'
        logging.debug(verdict)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы
    для работы программы. Если отсутствует хотя бы одна
    переменная окружения — функция вернет False, иначе — True.
    """
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        if PRACTICUM_TOKEN is None:
            logging.critical(
                'Отсутствует переменная окружения PRACTICUM_TOKEN'
            )
        if TELEGRAM_TOKEN is None:
            logging.critical(
                'Отсутствует переменная окружения TELEGRAM_TOKEN'
            )
        if TELEGRAM_CHAT_ID is None:
            logging.critical(
                'Отсутствует переменная окружения TELEGRAM_CHAT_ID'
            )
        return False


def main():
    """Основная логика работы бота."""

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except GetApiException:
            error_message = 'Получен некорректный ответ по запросу к API'
            logging.error(error_message)
            send_message(bot, error_message)
            time.sleep(RETRY_TIME)
            continue
        try:
            homeworks = check_response(response)
            if homeworks[0].get('status') != status:
                try:
                    status = homeworks[0].get('status')
                except ValueError as error:
                    error_message = f'Ошибка лоступа по ключу status {error}'
                    send_message(bot, error_message)
                    logging.error(error_message)
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.debug('Статус проверки домашки не изменился')
            time.sleep(RETRY_TIME)
        except CheckResponseException as error:
            error_message = f'Некорректный ответ API {error}'
            logging.error(error_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
