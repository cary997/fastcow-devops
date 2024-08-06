from fastapi import FastAPI, status
from fastapi.routing import APIRoute

from app.core import events
from app.core.config import settings
from app.core.exeption import Http422ErrorResponse


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# 实例化FastAPI实例
app = FastAPI(
    description=f"""{settings.SYS_DESCRIPTION}""",
    title=settings.SYS_TITLE,
    version=settings.SYS_VERSION,
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url=settings.SYS_OPENAPI_URL,
    generate_unique_id_function=custom_generate_unique_id,
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    responses={status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": Http422ErrorResponse}},
)

# 添加事件
app.add_event_handler("startup", events.startup(app))
app.add_event_handler("shutdown", events.stopping(app))
