def file_iterator(file_path: str, chunk_size: int = 5 * 1024 * 1024):
    """
    文件生成器
    :param file_path: 文件绝对路径
    :param offset: 文件读取的起始位置
    :param chunk_size: 文件读取的块大小
    :return: yield
    """
    with open(file_path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if data:
                yield data
            else:
                break
