import asyncio  # Для запуска асинхронных функций
import os  # Для чтения переменных окружения
from logging.config import fileConfig  # Для настройки логирования из файла alembic.ini

from sqlalchemy import pool  # Для управления пулом соединений
from sqlalchemy.engine import Connection  # Тип Connection (используется в аннотации)
from sqlalchemy.ext.asyncio import async_engine_from_config

# Создает асинхронный движок из конфига

from alembic import context  # Основной контекст Alembic (управляет миграциями)

# Получаем объект конфигурации Alembic (читает alembic.ini)
config = context.config

# Если указан файл конфигурации, настраиваем логирование по его правилам
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подключаем метаданные наших моделей для автогенерации миграций
# BaseModel.metadata содержит информацию обо всех таблицах проекта
from app.core.database.database import BaseModel
from app.modules import __all__  # Чтобы "увидеть" все модули с моделями

target_metadata = BaseModel.metadata  # Целевая "схема" БД для Alembic


def get_url() -> str:
    """
    Собираем строку подключения к базе данных из .env.
    Если переменные не заданы, берём "postgres" и "localhost" по умолчанию.
    """
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "postgres")
    # Формируем URL по шаблону asyncpg для асинхронного подключения
    return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}?async_fallback=True"


# Подставляем нашу строку подключения вместо статичной в alembic.ini
config.set_main_option("sqlalchemy.url", get_url())


def run_migrations_offline() -> None:
    """
    Оффлайн-режим: генерируем SQL-скрипты без реального подключения к БД.
    Полезно для проверки или CI, когда БД может быть недоступна.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,  # URL для подключения
        target_metadata=target_metadata,  # Схема моделей
        literal_binds=True,  # Подставить параметры прямо в SQL
        dialect_opts={"paramstyle": "named"},  # Стиль именованных параметров
    )

    # Открываем транзакцию и выполняем миграции (пишем SQL в stdout)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Вспомогательная функция: конфигурирует контекст с уже открытым соединением
    и выполняет миграции внутри транзакции.
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Онлайн-режим: создаём асинхронный движок, подключаемся к БД
    и запускаем миграции через do_run_migrations.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",  # Префикс для параметров в alembic.ini
        poolclass=pool.NullPool,  # Без пула соединений (для миграций это нормально)
    )

    # Открываем асинхронное соединение
    async with connectable.connect() as connection:
        # Передаём управление do_run_migrations
        await connection.run_sync(do_run_migrations)

    # Закрываем движок и освобождаем ресурсы
    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Обёртка для запуска асинхронных миграций в синхронном контексте.
    """
    asyncio.run(run_async_migrations())


# В зависимости от режима (offline/online) вызываем соответствующую функцию
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
