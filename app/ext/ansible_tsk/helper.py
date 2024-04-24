import os

from ansible.plugins.loader import module_loader


def get_modules_from_path(path):
    blacklisted_extensions = (".swp", ".bak", "~", ".rpm", ".pyc")
    blacklisted_prefixes = ("_",)

    assert os.path.isdir(path)

    sub_paths = list((os.path.join(path, p), p) for p in os.listdir(path))

    for path, name in sub_paths:
        if name.endswith(blacklisted_extensions):
            continue
        if name.startswith(blacklisted_prefixes):
            continue
        if os.path.isdir(path):
            for module in get_modules_from_path(path):
                yield module
        else:
            yield os.path.splitext(name)[0]


def list_ansible_modules() -> set[str]:
    paths = (p for p in module_loader._get_paths() if os.path.isdir(p))

    modules = set()

    for path in paths:
        modules.update(m for m in get_modules_from_path(path))

    return modules
