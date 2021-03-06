# homework_bot - бот для отслеживания статуса проверки проектов (домашних работ) Яндекс.Практикума
## Описание
```
Данный телеграм бот присылает пользователю статус последней отправленной для проверки
ревьюеру домашней работы. 
Запросы отправляются на эндпоинт https://practicum.yandex.ru/api/user_api/homework_statuses/
Возможные ответы бота:
- Работа проверена: ревьюеру всё понравилось. Ура!
- Работа взята на проверку ревьюером.
- Работа проверена: у ревьюера есть замечания.

Производится запись логгов
```
## Технологии
```
- Python 3.9

- python-dotenv версии 0.19.0
- python-telegram-bot версии 13.7
```
## Как запустить проект
Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/viserdi/homework_bot.git
```

```
cd homework_bot
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv env
```

```
source env/bin/activate
```

Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

Выполнить миграции:

```
python3 manage.py migrate
```

Запустить проект:

```
python3 manage.py runserver
```
