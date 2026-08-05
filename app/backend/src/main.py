from typing import Literal

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

from auth.routes import router as auth_router
from users.routes import router as users_router


class HealthResponse(BaseModel):
    status: Literal['ok']


api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth_router)
api_router.include_router(users_router)


@api_router.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the HTTP process is running; this does not probe PostgreSQL."""
    return HealthResponse(status='ok')


app = FastAPI(title='redid')
app.include_router(api_router)
