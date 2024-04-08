from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def get_dict_target_value(data: dict, key: str | None) -> Any:
    """
    深层次查找dict key
    return value
    """
    # 半段是否为字典
    if not isinstance(data, dict):
        raise TypeError(f"{data} is not dict!")
    # 判断data是否为空
    if not data:
        return None
    # key以.分割，传入数据应该为xxx.xxx这种格式
    if not key:
        raise TypeError("key is None!")
    keys = key.split(".")
    # 计数器
    count = 0
    for k in keys:
        count += 1
        if k in data:
            data = data[k]
            # 判断当前是否为keys中最后一位
            if count == len(keys):
                return data
        else:
            return None


class ToTree:
    """
    :param data:需要转换的数据
    :param is_sorted: 是否排序
    :param root_flag: 数据自身的标识
    :param sort_key: 按照key排序，key可以深层次例如"user.name"
    :param parent_flag: 数据父节点的标识
    :param parent_key: 数据父节点的name方便前端处理路由
    :param children_key: 转换后包含子数据的key
    :return: list 类型的 树嵌套数据
    """ ""

    def __init__(
        self,
        data: List = [],
        is_sorted: bool = False,
        sort_key: str | None = None,
        root_flag: str = "id",
        parent_flag: str = "parent",
        parent_key: str = "name",
        children_key: str = "children",
    ):
        self.data = data
        self.is_sorted = is_sorted
        self.sort_key = sort_key
        self.root_flag = root_flag
        self.parent_flag = parent_flag
        self.parent_key = parent_key
        self.chidren_key = children_key

    def list_to_tree(self) -> List[dict]:
        """
        转树形结构
        """
        # 先转成字典 id作为key, 数据作为value
        root = []
        node = []

        # 初始化数据，获取根节点和其他子节点list
        for _d in self.data:
            if not isinstance(_d, dict):
                _d = dict(_d)
            if not _d.get(self.parent_flag):
                root.append(_d)
            else:
                node.append(_d)
        # 查找子节点
        for _p in root:
            self.add_node(_p, node)

        # 无子节点
        if len(root) == 0:
            return node
        # 对根节点排序
        if self.is_sorted:
            root.sort(
                key=lambda x: (
                    get_dict_target_value(x, self.sort_key) is None,
                    get_dict_target_value(x, self.sort_key) == "",
                    get_dict_target_value(x, self.sort_key),
                )
            )
        return root

    def add_node(self, p, node) -> Any:
        """
        递归查找子节点
        """
        # 子节点list
        p[self.chidren_key] = []
        for _n in node:
            if _n.get(self.parent_flag) == p.get(self.root_flag):
                _n["parent_key"] = p.get(self.parent_key)
                p[self.chidren_key].append(_n)
        # 对子节点排序
        if len(p[self.chidren_key]) and self.is_sorted:
            p[self.chidren_key].sort(
                key=lambda x: (
                    get_dict_target_value(x, self.sort_key) is None,
                    get_dict_target_value(x, self.sort_key) == "",
                    get_dict_target_value(x, self.sort_key),
                )
            )
        # 递归子节点，查找子节点的节点
        for _t in p[self.chidren_key]:
            if not _t.get(self.chidren_key):
                _t[self.chidren_key] = []
            _t[self.chidren_key].append(self.add_node(_t, node))

        # 退出递归的条件
        if len(p[self.chidren_key]) == 0:
            return
