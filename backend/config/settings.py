"""
Настройки Django для проекта «Nornicel R&D Knowledge Graph».

Архитектурный принцип: Django ORM (SQLite/Postgres) отвечает за реляционную часть —
пользователи, роли, аудит действий (требование кейса по ИБ). Граф знаний хранится
отдельно в Neo4j и доступен через сервисный слой `knowledge/services/graph.py`.
"""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# .env лежит в корне репозитория (на уровень выше backend/). См. .env.example.
load_dotenv(BASE_DIR.parent / '.env')


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-change-me')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Сторонние
    'rest_framework',
    'corsheaders',
    # Приложения проекта
    'knowledge',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Реляционная БД для пользователей/ролей/аудита (граф знаний — в Neo4j отдельно).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS: фронтенд на React (Vite dev-сервер).
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173'
).split(',')

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}

# --- Neo4j (граф знаний) ---
NEO4J = {
    'uri': os.getenv('NEO4J_URI', ''),
    'user': os.getenv('NEO4J_USER', 'neo4j'),
    'password': os.getenv('NEO4J_PASSWORD', ''),
    'database': os.getenv('NEO4J_DATABASE', 'neo4j'),
}

# --- LLM (извлечение + NL→Cypher + синтез) ---
# Провайдер-агностичный слой (см. knowledge/services/llm/). Основной провайдер — YandexGPT
# через OpenAI-совместимый эндпоинт. Смена провайдера — переменной LLM_PROVIDER в .env.
_LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'yandex')
_YC_FOLDER_ID = os.getenv('YC_FOLDER_ID', '')
_LLM_MODEL = os.getenv('LLM_MODEL', '')
# Для YandexGPT имя модели можно собрать из folder_id, если LLM_MODEL не задан явно.
if not _LLM_MODEL and _LLM_PROVIDER == 'yandex' and _YC_FOLDER_ID:
    _LLM_MODEL = f'gpt://{_YC_FOLDER_ID}/yandexgpt/latest'

LLM = {
    'provider': _LLM_PROVIDER,
    'model': _LLM_MODEL,
    'api_base': os.getenv('LLM_API_BASE', 'https://llm.api.cloud.yandex.net/v1'),
    'api_key': os.getenv('LLM_API_KEY', ''),
    'folder_id': _YC_FOLDER_ID,
}

# --- Эмбеддинги (семантический поиск) ---
EMBEDDINGS = {
    'provider': os.getenv('EMBED_PROVIDER', 'local_e5'),
    'model': os.getenv('EMBED_MODEL', 'intfloat/multilingual-e5-large'),
}
