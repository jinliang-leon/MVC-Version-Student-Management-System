"""认证接口（Controller 层）—— 登录 / 注册 / 当前用户

路由前缀：/auth/（登录、注册为白名单，无需 JWT；/me 需登录）

本层只做：接收请求 -> 调用 user_service -> 序列化 -> 包装 success() 返回。
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.config import settings
from app.core.decorators import auth_required
from app.core.security import create_access_token
from app.services.user_service import user_service
from app.schemas.auth import (
    CurrentUserOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.views.response import ApiResponse, success
from app.views.serializers import user_to_out

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="用户登录",
    description="用户名密码登录，成功返回 JWT Token（有效期由 ACCESS_TOKEN_EXPIRE_MINUTES 控制）。",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = user_service.authenticate(db, payload.username, payload.password)
    # JWT 仅携带身份信息（sub + username）；角色/权限每次查库，权限变更即时生效
    token = create_access_token(user.user_id, user.username)
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
    description="创建新用户（密码自动 bcrypt 哈希存储）。角色不可自选，服务端强制绑定 student。",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = user_service.register(db, payload)
    return success(data=user_to_out(user), message="注册成功", code=201)


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
        is_super=any(r.is_system for r in user.roles),
    ).model_dump()
    return success(data=data, message="获取成功")
