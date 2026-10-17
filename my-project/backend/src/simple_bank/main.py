from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from simple_bank.api.v1.router import router as v1_router
from simple_bank.schemas.transfers import ApiError

app = FastAPI(title="Simple Bank Fund Transfer API")
app.include_router(v1_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def invalid_request_handler(request: Request, error: RequestValidationError) -> JSONResponse:
	response = ApiError(code="INVALID_REQUEST", message="The transfer request is invalid.")
	return JSONResponse(status_code=422, content=response.model_dump(mode="json"))
