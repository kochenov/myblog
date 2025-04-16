# /apps/backend/api/app/config.py

"""
Конфигурация проекта для блога на FastAPI.

Этот файл загружает настройки из файла .env и делает их доступными через объект settings.
Используйте этот объект во всём проекте для доступа к переменным окружения.
При деплое убедитесь, что файл .env НЕ попадает в систему контроля версий, добавив его в .gitignore.
"""

import secrets  # Для генерации случайных значений (секретные ключи)
import warnings  # Для вывода предупреждений

from typing import Annotated, Any, Literal  # Импортируем аннотации типов
from pydantic import (
    AnyUrl,  # Валидатор для URL
    BeforeValidator,  # Декоратор для предварительной обработки
    PostgresDsn,  # Валидатор для строки подключения к PostgreSQL
    computed_field,  # Декоратор для вычисляемых полей
    model_validator,  # Декоратор для дополнительной проверки модели
)
from pydantic_core import MultiHostUrl  # Для построения сложных URL
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)  # Базовые классы настроек
from typing_extensions import (
    Self,
)  # Для аннотации возвращаемого типа self при валидации


def parse_cors(v: Any) -> list[str] | str:
    """
    Преобразует строку с адресами, разделёнными запятыми, в список доменов.

    Аргументы:
        v: Значение CORS из файла .env (строка или список).

    Возвращает:
        Список доменов для разрешённых CORS.
    """
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError("Некорректный формат CORS")


class Settings(BaseSettings):
    """
    Класс настроек проекта.

    Этот класс автоматически загружает переменные из файла .env и проверяет их корректность.
    Изменять настройки можно без изменения исходного кода – достаточно обновить .env-файл.
    """

    # Чтение переменных из файла .env; файл должен находиться в корне проекта.
    # Рекомендуется добавить .env в .gitignore, чтобы секретные данные не попали в репозиторий.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,  # Игнорировать пустые значения
        extra="ignore",  # Игнорировать переменные, не описанные в модели
    )

    # --- Основные настройки API и проекта ---
    API_V1_STR: str = "/api/v1"  # Версия API
    # Если SECRET_KEY указан в .env, он перезапишет эту автогенерацию
    SECRET_KEY: str = secrets.token_urlsafe(32)
    REDIS_HOST: str = "localhost"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # Срок жизни токена: 8 дней

    # --- Настройки домена и окружения ---
    DOMAIN: str = "localhost"  # Домен приложения
    # Окружение приложения: local, staging или production.
    # Для безопасности обязательно изменяйте настройки при переходе в production.
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    SELENIUM_HUB_HOST: str = "http://localhost"
    CELERY_TASK_INTERVAL: int = 60
    CHROME_DRIVER: str = "local"

    @computed_field
    @property
    def server_host(self) -> str:
        """
        Вычисляемое поле для формирования URL сервера.

        Используется протокол http для локальной разработки, и https для staging/production.
        """
        if self.ENVIRONMENT == "local":
            return f"http://{self.DOMAIN}"
        return f"https://{self.DOMAIN}"

    # --- Настройки CORS ---
    # Переменная BACKEND_CORS_ORIGINS должна задаваться через .env в виде строки с доменами, разделёнными запятыми.
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
        []
    )

    # --- Параметры проекта ---
    PROJECT_NAME: str  # Название проекта, задается через .env
    SENTRY_DSN: AnyUrl | None = None  # DSN для Sentry, если используется

    # --- Настройки подключения к PostgreSQL ---
    POSTGRES_SERVER: str  # Сервер базы данных
    POSTGRES_USER: str  # Имя пользователя базы данных
    POSTGRES_PASSWORD: str  # Пароль пользователя
    POSTGRES_DB: str = (
        "blog_db"  # Название базы данных (если не задано, будет использоваться дефолтное)
    )
    POSTGRES_PORT: int = 5432  # Порт подключения к БД

    @computed_field
    @property
    def database_url(self) -> PostgresDsn:
        """
        Вычисляемое поле для формирования строки подключения к PostgreSQL.

        Используется схема подключения postgresql+asyncpg.
        """
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- Настройки отправки email ---
    SMTP_HOST: str | None = None  # SMTP-сервер (например, smtp.gmail.com)
    SMTP_PORT: int = 587  # Порт SMTP-сервера
    SMTP_USER: str | None = None  # Логин для SMTP-сервера
    SMTP_PASSWORD: str | None = None  # Пароль для SMTP-сервера
    EMAILS_FROM_EMAIL: str | None = None  # Email, с которого отправляются письма
    EMAILS_FROM_NAME: str | None = None  # Имя отправителя для писем

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        """
        Устанавливает имя отправителя по умолчанию, если оно не задано в .env.
        В данном проекте имя отправителя по умолчанию равно названию проекта.
        """
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48  # Время жизни токена для сброса пароля

    @computed_field
    @property
    def emails_enabled(self) -> bool:
        """
        Проверяет, можно ли отправлять email: активна функция, если заданы SMTP_HOST и EMAILS_FROM_EMAIL.
        """
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: str = (
        "test@example.com"  # Тестовый email для проверки конфигурации
    )

    # --- Настройки суперпользователя (администратора) ---
    FIRST_SUPERUSER: str  # Email суперпользователя (определяется в .env)
    FIRST_SUPERUSER_PASSWORD: str  # Пароль суперпользователя (определяется в .env)
    USERS_OPEN_REGISTRATION: bool = (
        False  # Определяет, разрешена ли свободная регистрация
    )

    # --- Дополнительные секреты ---
    RESET_PASSWORD_TOKEN_SECRET: str = secrets.token_urlsafe(32)
    VERIFICATION_TOKEN_SECRET: str = secrets.token_urlsafe(32)

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """
        Проверяет, не используется ли небезопасное значение по умолчанию
        для заданной переменной (var_name).
        """
        # Словарь подозрительных значений по умолчанию
        unsafe_defaults = {
            "SECRET_KEY": ["ваш_уникальный_секретный_ключ", "changeme", "secret"],
            "POSTGRES_PASSWORD": ["postgres", "password", "123456"],
            "FIRST_SUPERUSER_PASSWORD": ["admin", "admin123", "qwerty", "123456"],
        }

        if var_name in unsafe_defaults and value in unsafe_defaults[var_name]:
            message = (
                f"Значение переменной {var_name} установлено как небезопасное по умолчанию: '{value}'.\n"
                f"Пожалуйста, задайте надёжное значение в .env перед запуском в {self.ENVIRONMENT}-окружении."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=2)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        """
        Проверяет, что важные секретные параметры не используют значения по умолчанию.
        Это необходимо для обеспечения безопасности вашего блога.
        """
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        return self


# Создание глобального объекта настроек, который можно импортировать во всём проекте.
settings = Settings()  # type: ignore

# Рекомендация для разработчика:
# 1. При локальной разработке используйте .env с ENVIRONMENT=local.
# 2. Не забудьте добавить файл .env в .gitignore, чтобы секретные данные не попали в публичный репозиторий.
# 3. Для продакшена обязательно измените SECRET_KEY, POSTGRES_PASSWORD и FIRST_SUPERUSER_PASSWORD на надёжные значения.
# 4. При добавлении новых настроек:
#    - добавьте переменную в .env,
#    - объявите соответствующее поле в классе Settings, и
#    - используйте новые значения через объект settings.
