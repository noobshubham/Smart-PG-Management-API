"""Alembic migration environment.

Imports `Base` and every module's ORM models so autogenerate detects all tables.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.models import Base

# Import models so they register with Base.metadata.
from app.modules.auth import models as _auth_models  # noqa: F401
from app.modules.complaints import models as _complaint_models  # noqa: F401
from app.modules.finance import models as _finance_models  # noqa: F401
from app.modules.meals import models as _meal_models  # noqa: F401
from app.modules.notices import models as _notice_models  # noqa: F401
from app.modules.properties import models as _property_models  # noqa: F401
from app.modules.residents import models as _resident_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
