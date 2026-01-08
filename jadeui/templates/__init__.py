"""
JadeUI 内置模板
"""

import os

TEMPLATES_DIR = os.path.dirname(__file__)


def get_template_path(name: str) -> str:
    """获取内置模板路径"""
    return os.path.join(TEMPLATES_DIR, name)


def get_default_css() -> str:
    """获取默认 CSS 内容"""
    css_path = os.path.join(TEMPLATES_DIR, "default.css")
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()

