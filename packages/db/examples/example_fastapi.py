from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from packages.db.session import get_db
from packages.db.models.algorithm import Algorithm
from packages.schemas.algorithm import AlgorithmRead

router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.get("/{algorithm_id}", response_model=AlgorithmRead)
def get_algorithm(algorithm_id: int, db: Session = Depends(get_db)):
    algorithm = db.query(Algorithm).filter(
        Algorithm.id == algorithm_id
    ).first()

    if algorithm is None:
        raise HTTPException(status_code=404, detail="Algorithm not found")

    return algorithm
