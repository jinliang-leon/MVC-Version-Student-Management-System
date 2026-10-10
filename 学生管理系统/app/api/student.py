"""学生接口（Controller 层，6 个）

路由前缀：/students/

本层只做：接收请求 -> 调用 crud -> 包装 success() 返回。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db
from app.core.response import ApiResponse, success
from app.crud import crud_student
from app.schemas.common import PageResult
from app.schemas.student import StudentCreate, StudentOut, StudentUpdate

router = APIRouter(prefix="/students", tags=["学生管理"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[StudentOut]],
    summary="查询学生列表",
    description="分页查询所有学生，支持按姓名模糊搜索，可按班级ID、性别精确过滤。",
)
def list_students(
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（学生姓名）"),
    class_id: int | None = Query(None, description="按班级ID过滤"),
    gender: str | None = Query(None, description="按性别过滤：男/女"),
    include_deleted: bool = Query(False, description="是否包含已删除的学生"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_student.search(
            db,
            page=p.page,
            page_size=p.page_size,
            keyword=keyword,
            class_id=class_id,
            gender=gender,
            include_deleted=include_deleted,
        )
    )


@router.get(
    "/{student_id}",
    response_model=ApiResponse[StudentOut],
    summary="查询单个学生",
    description="根据学生ID查询单个学生的详细信息，含所属班级名称。",
)
def get_student(
    student_id: int = Path(..., description="学生ID"),
    include_deleted: bool = Query(False, description="是否包含已删除的学生"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_student.get_detail(db, student_id, include_deleted=include_deleted)
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[StudentOut],
    summary="新增学生",
    description="创建一个新学生。name 为必填；class_id 若填写则必须对应存在的班级。",
)
def create_student(
    payload: StudentCreate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_student.create_student(db, payload), message="学生创建成功", code=201
    )


@router.put(
    "/{student_id}",
    response_model=ApiResponse[StudentOut],
    summary="更新学生",
    description="按学生ID更新学生信息，只需传入需要修改的字段（局部更新）。",
)
def update_student(
    student_id: int = Path(..., description="学生ID"),
    payload: StudentUpdate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_student.update_student(db, student_id, payload), message="学生更新成功"
    )


@router.delete(
    "/{student_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除学生",
    description="逻辑删除学生（仅打删除标记，数据保留）。",
)
def delete_student(
    student_id: int = Path(..., description="学生ID"),
    db: Session = Depends(get_db),
):
    crud_student.delete_student(db, student_id)
    return success(data={"student_id": student_id}, message="学生删除成功")


@router.post(
    "/{student_id}/restore",
    response_model=ApiResponse[StudentOut],
    summary="恢复已删除的学生",
    description="将逻辑删除的学生恢复为正常状态（回收站功能）。",
)
def restore_student(
    student_id: int = Path(..., description="学生ID"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_student.restore_student(db, student_id), message="学生已恢复"
    )
