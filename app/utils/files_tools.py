import os
import shutil
import stat
import zipfile
from typing import Any, Optional

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from app.core.exeption import FilesOptionError


def mkdir_dir(
    path: str, mode: int = 0o755 | stat.S_IRUSR, exist_ok: bool = True
) -> Any:
    try:
        if not os.path.exists(path):
            os.makedirs(path, mode=mode, exist_ok=exist_ok)
    except Exception as e:
        logger.error(f"mkdir_dir error: {e}")
        raise FilesOptionError("创建目录失败")


def create_file(path: str, mode: int = 0o755 | stat.S_IRUSR) -> Any:
    try:
        print(path)
        if not os.path.exists(path):
            open(path, mode="a", encoding="utf-8").close()
            os.chmod(path, mode)
    except Exception as e:
        logger.error(f"create_file error: {e}")
        raise FilesOptionError(message="创建文件失败")


def remove_dir(path: str) -> Any:
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception as e:
        logger.error(f"remove_dir error: {e}")
        raise FilesOptionError(message="删除目录失败")


def remove_file(path: str) -> Any:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.error(f"remove_file error: {e}")
        raise FilesOptionError(message="删除文件失败")


def move_dir_or_file(src: str, dst: str) -> Any:
    try:
        shutil.move(src, dst)
    except Exception as e:
        logger.error(f"move_dir_or_file error: {e}")
        raise FilesOptionError(message="移动文件或目录失败")


def rename_file_or_dir(src: str, dst: str) -> Any:
    try:
        os.rename(src, dst)
    except Exception as e:
        logger.error(f"rename_file_or_dir error: {e}")
        raise FilesOptionError(message="删除文件或目录失败")


class DirFilesTree(BaseModel):
    """
    目录树结构
    """

    model_config = ConfigDict(extra="ignore")
    name: str = Field(default=..., description="名称")
    path: str = Field(default=..., description="相对路径")
    type: Optional[int] = Field(..., description="类型")
    parent: Optional[str] = Field(default=None, description="父路径")
    children: Optional[list[dict]] = Field(default=[], description="子节点")


def dir_to_tree(path: str, root_name: str = None) -> dict:
    """
    读取目录树形结构
    type 1 表示根 2表示目录 3表示文件
    """
    root_dir = DirFilesTree(
        name=root_name if root_name else os.path.basename(path),
        path=os.path.basename(path),
        type=1,
        parent=None,
        children=[],
    )

    if not os.listdir(path):
        return root_dir.model_dump()

    def get_children(c_path: str, c_dirs: DirFilesTree, parent_path: str) -> dict:
        for i in os.listdir(c_path):
            temp_path = os.path.join(c_path, i)
            if os.path.isdir(temp_path):
                temp_dir = DirFilesTree(
                    name=os.path.basename(temp_path),
                    path=os.path.join(parent_path, i),
                    type=2,
                    parent=parent_path,
                )
                c_dirs.children.append(get_children(temp_path, temp_dir, temp_dir.path))
            if os.path.isfile(temp_path):
                temp = DirFilesTree(
                    name=os.path.basename(temp_path),
                    path=os.path.join(parent_path, i),
                    type=3,
                    parent=parent_path,
                )

                c_dirs.children.append(temp.model_dump())
        return c_dirs.model_dump()

    return get_children(path, root_dir, root_dir.path)


def make_dir_zip(dir_path: str, out_path: str):
    """
    压缩指定文件夹
    :param dir_path: 目标文件夹路径
    :param out_path: 压缩文件保存路径+.zip
    :return: 无
    """
    try:
        new_zip = zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED)
        for path, dir_names, filenames in os.walk(dir_path):
            # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
            file_path = path.replace(dir_path, "")

            for filename in filenames:
                new_zip.write(
                    os.path.join(path, filename), os.path.join(file_path, filename)
                )
        new_zip.close()
    except Exception as e:
        logger.error(f"zip dir error: {e}")
        raise FilesOptionError(message="压缩目录失败")


def get_file_lang(path: str) -> str:
    if path.endswith(".py"):
        return "python"
    if path.endswith(".md"):
        return "markdown"
    if path.endswith(".yaml") or path.endswith(".yml"):
        return "yaml"
    if path.endswith(".json"):
        return "json"
    if path.endswith(".sql"):
        return "sql"
    if path.endswith(".j2"):
        return "jinja2"
    return "shell"
