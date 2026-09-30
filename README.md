# NEON CRATE — пародия на кейс-сайты (Django + SQLite)

Весь проект лежит в одной папке `neoncrate/`. Команды ниже выполняйте из неё.

```
cd neoncrate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

## Структура проекта

```
neoncrate/
├── manage.py
├── requirements.txt
├── db.sqlite3                 база (уже заполнена)
├── case-battle-data.json      исходные данные 741 предметов / 18 кейсов
├── neoncases/                 настройки Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── cases/                     приложение
│   ├── models.py
│   ├── views.py
│   ├── services.py            ролл и шансы
│   ├── signals.py
│   ├── admin.py
│   ├── urls.py / auth_urls.py / promo_urls.py
│   ├── migrations/
│   └── management/commands/seed_data.py
├── templates/                 HTML
├── static/                    css / js
└── staticfiles/               collectstatic (создаётся автоматически)
```

Учебный/пародийный проект. Не связан с Valve Corporation, реальные деньги не принимаются,
вывод средств не предусмотрен. Все балансы вымышленные.

## Локальный запуск

```
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data      # 741 предмет, 18 кейсов, промокоды, розыгрыши, турниры
python manage.py createsuperuser
python manage.py runserver
```

## Ключевые файлы

| Путь | Назначение |
|---|---|
| `neoncases/settings.py` | настройки; прод-значения берутся из env |
| `cases/models.py` | Skin, Case, CaseItem (веса), Profile, InventoryItem, Drop, Promo, Giveaway, Tournament |
| `cases/services.py` | взвешенный ролл `roll_case`, расчёт шансов апгрейда |
| `cases/views.py` | страницы + JSON-эндпоинт открытия кейса |
| `cases/management/commands/seed_data.py` | загрузка данных из `case-battle-data.json` |
| `static/css/neon.css` | неоновая тема |
| `static/js/roulette.js` | анимация рулетки |

## Шансы

Вес предмета = `1 / цена^0.8` (с нижним порогом). Точная вероятность каждого предмета
показана в колонке «%» на странице кейса. Пример по кейсу Lonestar: самый дорогой предмет
≈ 0.24%, самый дешёвый ≈ 7.6%.

## Промокоды

`NEON-START` (5000), `CRATE-500` (500), `FREE-SPIN` (250), `GLOW-10` (+10%), `SHADOW-13` (+13%).
Каждый код можно активировать один раз на аккаунт.

## Тесты

```
python manage.py test cases
```

## Деплой на PythonAnywhere

1. Залейте проект в репозиторий (GitHub), затем на PythonAnywhere: **Web → Create new Web app → Manual configuration**, выберите ту же версию Python, что и локально.
2. **Bash console**:
   ```
cd ~/neoncrate
    python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py seed_data
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```
3. **Web → WSGI config file**: замените содержимое на
   ```python
   import os
   import sys
   path = os.path.expanduser('~/neoncrate')
   sys.path.insert(0, path)
   os.environ['DJANGO_SETTINGS_MODULE'] = 'neoncases.settings'
   os.environ['DEBUG'] = '0'
   os.environ['SECRET_KEY'] = 'сгенерируйте-длинную-случайную-строку'
   os.environ['ALLOWED_HOSTS'] = 'ваш-юзернейм.pythonanywhere.com'
   os.environ['CSRF_TRUSTED_ORIGINS'] = 'https://ваш-юзернейм.pythonanywhere.com'
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
   Впишите `sys.path.insert(0, os.path.expanduser('~/venv/lib/python3.X/site-packages'))`, если venv не подхватился автоматически.
4. **Web → Settings**: Source Code = `~/neoncrate`, Working Directory = `~/neoncrate`, `Serve static files` через **WhiteNoise** (см. ниже) либо через встроенный mapping `/static/` → `~/neoncrate/staticfiles`.
5. Reload.

### WhiteNoise (рекомендуется)

Добавьте в `requirements.txt`:
```
whitenoise>=6.6
```
и в `neoncases/settings.py` в список `INSTALLED_APPS` — `'whitenoise.runserver_nostatic'`, а в `MIDDLEWARE` — сразу после `SecurityMiddleware`:
```python
'whitenoise.middleware.WhiteNoiseMiddleware',
```
Плюс в `STORAGES`:
```python
'staticfiles': {
    'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
},
```
Это убирает необходимость в ручном static mapping.

## Заметки

- Загруженные 741 предмет и 15 кейсов — реальные изображения с публичного CDN `cdn6.gamecontent.io`, они принадлежат своим владельцам и используются в ироничных целях. Для публичного запуска в коммерческих целях замените их на собственные ассеты.
- Баланс при регистрации — 10 000 NEON, пополнение возможно только промокодами.