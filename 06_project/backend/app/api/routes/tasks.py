from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.task_run import TaskRun
from app.schemas.task import (
    DynamicTaskRequest,
    TaskDefinitionResponse,
    TaskHistoryListResponse,
    TaskRunResponse,
    TaskTriggerRequest,
)
from app.services.task_registry import (
    get_task_definition,
    get_task_definitions,
    get_task_handler,
)
from app.services.task_runner import TaskRunnerService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _execute_named_task(
    db: Session,
    task_name: str,
    params: dict,
) -> TaskRun:
    definition = get_task_definition(task_name)
    handler = get_task_handler(task_name)

    def logic(logger):
        if definition is None:
            logger(
                f"No registered handler for '{task_name}'; using generic runner.",
                "WARNING",
            )
        return handler(logger, params)

    return TaskRunnerService.execute_task(db, task_name, logic, payload=params)


@router.post("/health-check", response_model=TaskRunResponse)
def run_health_check(db: Session = Depends(get_db)) -> TaskRun:
    return _execute_named_task(db, "health_check", {})


@router.post("/sync", response_model=TaskRunResponse)
def run_data_sync(
    payload: TaskTriggerRequest | None = None,
    db: Session = Depends(get_db),
) -> TaskRun:
    params = payload.params if payload and payload.params else {}
    return _execute_named_task(db, "sync_data", params)


@router.post("/process-files", response_model=TaskRunResponse)
def run_file_processing(db: Session = Depends(get_db)) -> TaskRun:
    return _execute_named_task(db, "process_files", {})


@router.post("/e2e-test", response_model=TaskRunResponse)
def run_e2e_test(db: Session = Depends(get_db)) -> TaskRun:
    return _execute_named_task(db, "e2e_test", {})


@router.get("/definitions", response_model=list[TaskDefinitionResponse])
def list_task_definitions() -> list[TaskDefinitionResponse]:
    return [
        TaskDefinitionResponse(
            name=definition.name,
            label=definition.label,
            description=definition.description,
            params_hint=definition.params_hint,
        )
        for definition in get_task_definitions()
    ]


@router.post("/execute", response_model=TaskRunResponse)
def execute_dynamic_task(
    payload: DynamicTaskRequest,
    db: Session = Depends(get_db),
) -> TaskRun:
    return _execute_named_task(db, payload.task_name, payload.params)


@router.get("/history", response_model=TaskHistoryListResponse)
def get_task_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    total = db.query(TaskRun).count()
    items = (
        db.query(TaskRun)
        .options(selectinload(TaskRun.logs))
        .order_by(TaskRun.started_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": items}
