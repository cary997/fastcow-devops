# file 参数类型是字节 bytes
import os
from mimetypes import guess_type
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Body, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger

from app.apis.files.files_desp import file_iterator
from app.apis.files.files_schema import (
    ReadFile,
    ReadFileResponse,
    ReadFileResult,
    VerifyFileResponse,
    VerifyFileResult,
)
from app.core.base import ResponseBase
from app.core.config import base_path
from app.utils.files_tools import create_file, get_file_lang, make_dir_zip, mkdir_dir

router = APIRouter()


@router.post("/verify", summary="文件校验", response_model=VerifyFileResponse)
async def verify_file(file_hash: str = Query(..., description="文件hash")):
    """文件校验"""
    path = Path(base_path.upload_temp_path, file_hash)
    chunks = []
    if os.path.exists(path):
        chunks = os.listdir(path)
        chunks = sorted(chunks, key=lambda x: int(x.split("_")[-1]))
        if len(chunks) > 1:
            del chunks[-1]
    return VerifyFileResponse(
        message="校验完成", data=VerifyFileResult(file_hash=file_hash, chunks=chunks)
    ).success()


@router.post("/upload", summary="文件分片上传", response_model=ResponseBase)
async def upload_file(
    file_hash: str = Body(..., description="文件hash"),
    chunk_hash: str = Body(..., description="file_hash + chunk序号"),
    chunk: UploadFile = File(..., description="分片文件"),
):
    """文件分片上传"""
    path = Path(base_path.upload_temp_path, file_hash)
    mkdir_dir(str(path))
    file_name = Path(path, chunk_hash)
    if not os.path.exists(file_name):
        context = await chunk.read()
        async with aiofiles.open(file_name, "wb") as f:
            await f.write(context)
    return ResponseBase(message="上传分片成功", data={"chunk": chunk_hash}).success()


@router.put("/merge", summary="合并分片文件", response_model=ResponseBase)
async def merge_file(
    file_name: str = Body(..., description="文件名称"),
    file_hash: str = Body(..., description="文件hash"),
    target_path: str = Body(..., description="目标文件路径"),
):
    """合并分片文件"""
    mkdir_dir(target_path)
    target_file_name = Path(target_path, file_name)
    path = Path(base_path.upload_temp_path, file_hash)
    try:
        if os.path.isdir(path) and len(os.listdir(path)):
            async with aiofiles.open(
                target_file_name, "wb+"
            ) as target_file:  # 打开目标文件
                for i in range(len(os.listdir(path))):
                    temp_file_name = Path(path, f"{file_hash}_{i}")
                    async with aiofiles.open(
                        temp_file_name, "rb"
                    ) as temp_file:  # 按序打开每个分片
                        data = await temp_file.read()
                        await target_file.write(data)  # 分片 内容写入目标文件
                # remove_dir(str(path))  # 删除临时目录
        else:
            create_file(str(target_file_name))
    except Exception as e:
        logger.error(f"merge_file error: {e}")
        return ResponseBase(message=f"合并文件失败 {e}").fail()
    return ResponseBase(message="上传文件成功", data={"file_name": file_name}).success()


@router.post("/read", summary="读取文件", response_model=ReadFileResponse)
async def read_file(post: ReadFile):
    path = Path(post.path)
    if not os.path.exists(path):
        return ReadFileResponse(message="文件不存在").fail()
    async with aiofiles.open(path, "rb") as file:
        code = await file.read()
        lang = get_file_lang(str(path))
        await file.close()
    return ReadFileResponse(
        message="读取文件成功", data=ReadFileResult(code=code, lang=lang)
    ).success()


@router.post("/write", summary="写入文件", response_model=ReadFileResponse)
async def write_file(
    path: str = Body(..., description="文件路径"),
    code: bytes | str = Body(..., description="文件内容"),
):
    path = Path(path)
    if not os.path.exists(path):
        return ReadFileResponse(message="文件不存在").fail()
    if isinstance(code, str):
        code = bytes(code, encoding="utf8")
    async with aiofiles.open(path, "wb") as file:
        await file.write(code)
        lang = get_file_lang(str(path))
        await file.close()
    return ReadFileResponse(
        message="写入文件成功", data=ReadFileResult(code=code, lang=lang)
    ).success()


@router.get("/downloads", summary="下载文件", response_class=StreamingResponse)
async def download_file(file_path: str = Query(..., description="文件路径或目录路径")):
    """下载文件"""
    if not file_path.startswith(base_path.base_path):
        return ResponseBase(message="非法路径").fail()
    if not os.path.exists(file_path):
        return ResponseBase(message="路径不存在").fail()
    if os.path.isdir(file_path):
        out_path = os.path.join(base_path.download_tmp_path, os.path.basename(file_path))
        make_dir_zip(file_path, f"{out_path}.zip")
        file_path = f"{out_path}.zip"
    filename = os.path.basename(file_path)
    content_type, encoding = guess_type(file_path)
    content_type = content_type or "application/octet-stream"
    # 检查文件是否存在
    return StreamingResponse(
        file_iterator(file_path),
        media_type=content_type,
        headers={
            "content-disposition": f'attachment; filename="{filename}"',
            "accept-ranges": "bytes",
            "connection": "keep-alive",
            "filename": filename,
            "Access-Control-Expose-Headers": "filename",
        },
    )
