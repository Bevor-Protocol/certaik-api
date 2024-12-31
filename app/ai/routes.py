from fastapi import APIRouter

from app.utils.types import EvalBody

from .services.eval import process_evaluation

router = APIRouter()


@router.post("/eval")
async def evaluate_contract_raw(data: EvalBody):
    return await process_evaluation(data)
