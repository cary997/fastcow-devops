from fastapi import APIRouter

router = APIRouter()


@router.post("/add", summary="添加主机信息")
async def assets_host_add():
    pass
