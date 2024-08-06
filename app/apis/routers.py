from fastapi import APIRouter, Security

from app.depends import check_token_dep

from .assets import assetsRouter
from .auth import authRouters
from .files import filesRouters
from .login import login_api
from .system import systemRouter
from .tasks import tasksRouters

loginRouter = APIRouter()
loginRouter.include_router(login_api.router, tags=["login"])

apiRouter = APIRouter(dependencies=[Security(check_token_dep)])
apiRouter.include_router(authRouters, prefix="/auth", tags=["auth"])
apiRouter.include_router(assetsRouter,prefix="/assets",tags=["assets"])
apiRouter.include_router(filesRouters, prefix="/files", tags=["files"])
apiRouter.include_router(tasksRouters, prefix="/tasks", tags=["tasks"])
apiRouter.include_router(systemRouter, prefix="/system", tags=["system"])
