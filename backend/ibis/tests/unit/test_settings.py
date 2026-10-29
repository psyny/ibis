from infrastructure.config.settings import Settings


def test_database_url_gets_explicit_psycopg2_driver():
    for raw in ("postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"):
        assert Settings(database_url=raw).sqlalchemy_url == "postgresql+psycopg2://u:p@h:5432/db"
    assert Settings(database_url="postgresql+psycopg2://u:p@h/db").sqlalchemy_url == "postgresql+psycopg2://u:p@h/db"
    assert Settings(database_url="sqlite:///x.db").sqlalchemy_url == "sqlite:///x.db"
