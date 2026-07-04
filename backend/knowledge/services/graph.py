"""
Сервисный слой доступа к Neo4j. Один драйвер на процесс; сессия — на запрос.
"""
from django.conf import settings
from neo4j import GraphDatabase

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        cfg = settings.NEO4J
        _driver = GraphDatabase.driver(
            cfg['uri'], auth=(cfg['user'], cfg['password'])
        )
    return _driver


def run(cypher: str, params: dict | None = None) -> list[dict]:
    """Выполнить Cypher и вернуть записи как список словарей."""
    cfg = settings.NEO4J
    with get_driver().session(database=cfg['database']) as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def verify_connectivity() -> None:
    get_driver().verify_connectivity()


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
