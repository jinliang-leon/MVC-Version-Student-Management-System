"""认证接口（Controller 层）—— 登录 / 注册 / 当前用户

路由前缀：/auth/（登录、注册为白名单，无需 JWT；/me 需登录）
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.decorators import auth_required
from app.core.response import ApiResponse, success
from app.core.security import create_access_token
from app.crud import crud_user
from app.schemas.auth import (
    CurrentUserOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    user_to_out,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="用户登录",
    description="用户名密码登录，成功返回 JWT Token（有效期由 ACCESS_TOKEN_EXPIRE_MINUTES 控制）。",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = crud_user.authenticate(db, payload.username, payload.password)
    token = create_access_token(user.user_id, [r.code for r in user.roles])
    return success(
        data={
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
        message="登录成功",
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[UserOut],
    summary="用户注册",
    description="创建新用户（密码自动 bcrypt 哈希存储）。注意：开放注册意味着任何人可创建账号，生产环境建议关闭或仅用于初始化。",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = crud_user.create_user(db, payload)
    return success(data=user_to_out(user).model_dump(), message="注册成功", code=201)


@router.get(
    "/me",
    response_model=ApiResponse[CurrentUserOut],
    summary="当前登录用户",
    description="返回当前登录用户及其角色码、权限码（经全部角色汇总去重）。",
)
@auth_required
def me(request: Request):
    user = request.state.user
    data = CurrentUserOut(
        user_id=user.user_id,
        username=user.username,
        roles=user.role_codes,
        permissions=sorted(user.permission_codes),
        is_active=user.is_active,
    ).model_dump()
    return success(data=data, message="获取成功")
