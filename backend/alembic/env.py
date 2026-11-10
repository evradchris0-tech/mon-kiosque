from alembic import context
from sqlalchemy import create_engine

from app.core.config import parametres
from app.db import modeles  # noqa: F401
from app.db.base import Base

cible = Base.metadata
url = parametres().database_url


def run() -> None:
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=cible, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    with create_engine(url).connect() as connexion:
        context.configure(connection=connexion, target_metadata=cible)
        with context.begin_transaction():
            context.run_migrations()


run()
