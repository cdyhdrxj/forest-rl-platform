from sqlalchemy import select

from packages.db.session import db_session
from packages.db.models.algorithm import Algorithm
from packages.db.models.enums import AlgorithmFamily, ProjectMode


def create_algorithm():
    with db_session() as db:
        algo = Algorithm(
            code="binsearch",
            name="Binary Search",
            family=AlgorithmFamily.hybrid,
            mode=ProjectMode.robot,
            framework="framework",
            description="Binary Search"
        )

        db.add(algo)


def list_algorithms():
    with db_session() as db:
        algos = db.execute(select(Algorithm)).scalars().all()
        algos = db.query(Algorithm).all()

        for a in algos:
            print(a.id, a.name)


create_algorithm()
print("Алгоритм добавлен")
list_algorithms()
