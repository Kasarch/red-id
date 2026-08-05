from typing import Annotated

from fastapi import APIRouter, Depends

from auth.dependencies import CurrentUser, SessionDependency
from users.repository import UserRepository
from users.schemas import UserResponse, UserUpdate
from users.service import UserService

router = APIRouter(prefix='/users', tags=['users'])


def get_user_service(session: SessionDependency) -> UserService:
    return UserService(session, UserRepository(session))


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]


@router.get('/me', response_model=UserResponse)
def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch('/me', response_model=UserResponse)
async def update_me(
    request: UserUpdate,
    current_user: CurrentUser,
    service: UserServiceDependency,
) -> UserResponse:
    avatar_url = str(request.avatar_url) if request.avatar_url is not None else None
    user = await service.update_avatar(current_user, avatar_url)
    return UserResponse.model_validate(user)
