"""RBAC 种子脚本：建表 + 初始化权限 / 角色 / 初始管理员

用法（在项目根目录执行）：
    python seed_rbac.py

幂等：已存在的权限 / 角色会跳过，权限映射会收敛到本文定义的状态，可重复执行。
初始管理员账号来自 settings.ADMIN_USERNAME / ADMIN_PASSWORD（默认 admin / admin123），
若仍为默认密码，脚本会强提示修改。
"""
import logging
import sys
from pathlib import Path

# 把项目根目录加入搜索路径，保证能 import app（本文件就在项目根目录下，与 app/main.py 的做法一致）
sys.path.append(str(Path(__file__).resolve().parent))

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.crud.permission import crud_permission
from app.crud.role import crud_role
from app.crud.user import crud_user
from app.models.role import Role
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed_rbac")

# 权限目录：module -> [(code, name), ...]
PERMISSIONS = {
    "class": [
        ("class:list", "查询班级列表"),
        ("class:read", "查看班级详情"),
        ("class:create", "新增班级"),
        ("class:update", "更新班级"),
        ("class:delete", "删除班级"),
        ("class:restore", "恢复班级"),
    ],
    "student": [
        ("student:list", "查询学生列表"),
        ("student:read", "查看学生详情"),
        ("student:create", "新增学生"),
        ("student:update", "更新学生"),
        ("student:delete", "删除学生"),
        ("student:restore", "恢复学生"),
    ],
    "teacher": [
        ("teacher:list", "查询教师列表"),
        ("teacher:read", "查看教师详情"),
        ("teacher:create", "新增教师"),
        ("teacher:update", "更新教师"),
        ("teacher:delete", "删除教师"),
        ("teacher:restore", "恢复教师"),
    ],
    "score": [
        ("score:list", "查询成绩列表"),
        ("score:read", "查看成绩详情"),
        ("score:create", "新增成绩"),
        ("score:update", "更新成绩"),
        ("score:delete", "删除成绩"),
        ("score:restore", "恢复成绩"),
    ],
    "employment": [
        ("employment:list", "查询就业记录列表"),
        ("employment:read", "查看就业记录详情"),
        ("employment:create", "新增就业记录"),
        ("employment:update", "更新就业记录"),
        ("employment:delete", "删除就业记录"),
        ("employment:restore", "恢复就业记录"),
    ],
    "stats": [
        ("stats:view", "查看统计分析"),
    ],
    "role": [
        ("role:list", "查询角色列表"),
        ("role:read", "查看角色详情"),
        ("role:create", "新增角色"),
        ("role:update", "更新角色"),
        ("role:delete", "删除角色"),
        ("role:assign-permission", "分配角色权限"),
    ],
    "permission": [
        ("permission:list", "查询权限列表"),
    ],
    "user": [
        ("user:list", "查询用户列表"),
        ("user:read", "查看用户详情"),
        ("user:assign-role", "分配用户角色"),
    ],
}


def _codes(*modules: str) -> list[str]:
    """取指定模块的全部权限码"""
    return [code for m in modules for code, _ in PERMISSIONS[m]]


def _read_codes(*modules: str) -> list[str]:
    """取指定模块的只读权限码（list + read）"""
    codes: list[str] = []
    for m in modules:
        codes += [f"{m}:list", f"{m}:read"]
    return codes


# 角色定义
ROLES = [
    {
        "code": "super_admin",
        "name": "超级管理员",
        "description": "拥有系统全部权限",
        "is_system": True,
        "permissions": _codes(*list(PERMISSIONS.keys())),
    },
    {
        "code": "admin",
        "name": "管理员",
        "description": "管理全部业务数据与用户，不含角色管理",
        "is_system": False,
        "permissions": _codes("class", "student", "teacher", "score", "employment", "stats")
        + _codes("permission")
        + _codes("user"),
    },
    {
        "code": "teacher",
        "name": "教师",
        "description": "查看班级/学生/教师/就业，可管理成绩，查看统计",
        "is_system": False,
        "permissions": _read_codes("class", "student", "teacher", "employment")
        + _codes("score")
        + ["stats:view"],
    },
    {
        "code": "student",
        "name": "学生",
        "description": "查看五张业务表与统计",
        "is_system": False,
        "permissions": _read_codes("class", "student", "teacher", "score", "employment")
        + ["stats:view"],
    },
]


def _seed_permissions(db) -> None:
    for module, codes in PERMISSIONS.items():
        for code, name in codes:
            crud_permission.get_or_create(db, code=code, name=name, module=module)
    log.info("权限初始化完成（共 %d 个）", sum(len(c) for c in PERMISSIONS.values()))


def _seed_roles(db) -> None:
    for spec in ROLES:
        role = crud_role.get_by_code(db, spec["code"])
        if role is None:
            role = Role(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                is_system=spec["is_system"],
            )
            db.add(role)
            db.flush()
            log.info("创建角色: %s（%s）", spec["code"], spec["name"])
        # 权限映射收敛到本文定义（幂等）
        perms = [crud_permission.get_by_code(db, c) for c in spec["permissions"]]
        role.permissions = [p for p in perms if p is not None]
        db.add(role)
    db.commit()
    log.info("角色初始化完成（共 %d 个）", len(ROLES))


def _seed_admin(db) -> None:
    admin = crud_user.get_by_username(db, settings.ADMIN_USERNAME)
    if admin is None:
        admin = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        log.info("创建初始管理员: %s", settings.ADMIN_USERNAME)
    else:
        log.info("初始管理员已存在: %s", settings.ADMIN_USERNAME)

    super_role = crud_role.get_by_code(db, "super_admin")
    if super_role is not None and "super_admin" not in admin.role_codes:
        admin.roles.append(super_role)
        db.add(admin)
        db.commit()
        log.info("已为 %s 授予 super_admin 角色", settings.ADMIN_USERNAME)

    if settings.ADMIN_PASSWORD == "admin123":
        log.warning("[警告] 初始管理员仍在使用默认密码 admin123，请尽快修改！")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_permissions(db)
        _seed_roles(db)
        _seed_admin(db)
    finally:
        db.close()
    log.info("RBAC 初始化完成")


if __name__ == "__main__":
    main()
