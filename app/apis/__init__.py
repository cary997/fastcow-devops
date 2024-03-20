from fastapi import APIRouter, Security

from .auth import authRouters
from .deps import CheckTokenDep
from .login import login_api
from .system import systemRouter

loginRouter = APIRouter()
loginRouter.include_router(login_api.router, tags=["login"])

apiRouter = APIRouter(dependencies=[Security(CheckTokenDep)])
apiRouter.include_router(authRouters, prefix="/auth", tags=["auth"])
apiRouter.include_router(systemRouter, prefix="/system", tags=["system"])
