from app.database import Base, engine
from app import models

target_metadata=Base.metadata

def run_migrations_online():
    from alembic import context
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction(): context.run_migrations()
run_migrations_online()
