from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.ai.eval import EvalService

# from app.api.ai.webhook import process_webhook_replicate
from app.api.depends.auth import require_auth
from app.pydantic.request import EvalBody
from app.pydantic.response import EvalResponse
from app.utils.enums import ResponseStructureEnum


class AiRouter:

    def __init__(self):
        self.router = APIRouter(prefix="/ai", tags=["ai"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/eval",
            self.process_ai_eval,
            methods=["POST"],
            dependencies=[Depends(require_auth)],
        )
        self.router.add_api_route(
            "/eval/{id}",
            self.get_eval_by_id,
            methods=["GET"],
            params={"add_agent_security_score": bool},
        )
        # self.router.add_api_route(
        #     "/eval/webhook",
        #     self.process_webhook,
        #     methods=["POST"],
        #     include_in_schema=False,
        # )

    async def process_ai_eval(
        self,
        request: Request,
        data: EvalBody,
    ):
        eval_service = EvalService()
        response = await eval_service.process_evaluation(
            user=request.scope["auth"], data=data
        )

        return JSONResponse(response, status_code=202)

    async def get_eval_by_id(self, request: Request, id: str) -> EvalResponse:
        response_type = request.query_params.get(
            "response_type", ResponseStructureEnum.JSON.name
        )
        agent_security_score = (
            request.query_params.get("add_agent_security_score", "false").lower()
            == "true"
        )

        try:
            response_type = ResponseStructureEnum._value2member_map_[response_type]
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid response_type parameter"
            )

        eval_service = EvalService()
        response = await eval_service.get_eval(id, response_type=response_type)
        result = response.model_dump()["result"]["result"]

        if agent_security_score:
            from app.api.ai.agent_sec import AgentSecurityService

            agent_service = AgentSecurityService()
            try:
                # Assuming twitter handle is available in the result
                twitter_handle = result.get("twitter_handle")
                if twitter_handle:
                    score = agent_service.calculate_agent_sec_score(
                        twitter_handle, 85.0
                    )  # Default audit score
                    result["agent_security_score"] = score
                    result["project_type"] = "Agent"
                else:
                    result["agent_security_score"] = None
                    result["project_type"] = "Protocol"
            except Exception as e:
                result["agent_security_score"] = None
                result["project_type"] = "Agent"
        else:
            result["project_type"] = "Protocol"

        return JSONResponse(result, status_code=200)

    # async def process_webhook(self, request: Request):
    #     """
    #     Internal webhook endpoint for Replicate model predictions.
    #     This route should not be called directly - it is used by the Replicate service
    #     to deliver prediction results.
    #     """

    #     chained_call = request.query_params.get("chained_call")

    #     body = await request.json()
    #     response = await process_webhook_replicate(
    #         data=Prediction(**body), webhook_url=chained_call
    #     )
    #     return response
