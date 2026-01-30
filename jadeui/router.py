"""
JadeUI Router - 后端主导的路由系统

支持两种模式：
1. 内置模板模式 (默认) - 自动生成带侧边栏的应用框架
2. 自定义模式 - 用户提供自己的 HTML 模板，Router 只处理路由逻辑

Example (内置模板):
    router = Router()
    router.page("/", "pages/home.html", title="首页", icon="🏠")
    router.mount(title="My App", web_dir="web")

Example (自定义模板):
    router = Router()
    router.page("/", "pages/home.html")
    router.mount(
        web_dir="web",
        template="my_app.html",  # 用户自定义模板
    )
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional

from .ipc import IPCManager
from .server import LocalServer
from .window import Backdrop, Theme, Window

logger = logging.getLogger(__name__)

# 内置模板目录
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


@dataclass
class PageConfig:
    """页面配置"""

    path: str
    template: str
    title: str = "Page"
    icon: str = ""
    show_in_nav: bool = True


class Router:
    """后端主导的路由器

    支持两种使用方式：

    1. 内置模板模式 (默认):
       自动生成带标题栏、侧边栏的应用框架

       router = Router()
       router.page("/", "pages/home.html", title="首页", icon="🏠")
       router.mount(title="My App", web_dir="web")

    2. 自定义模板模式:
       使用用户提供的 HTML 模板，Router 只处理路由逻辑

       router = Router()
       router.page("/", "pages/home.html")
       router.mount(
           web_dir="web",
           template="my_app.html",  # 用户的模板文件
       )

    用户模板需要:
    - 引入 jadeui.css 和 jadeui.js
    - 包含 id="page-content" 的元素用于渲染页面
    """

    def __init__(self, ipc: Optional[IPCManager] = None):
        self.ipc = ipc or IPCManager()
        self.server = LocalServer()

        self._pages: List[PageConfig] = []
        self._current_route: str = "/"
        self._window: Optional[Window] = None
        self._web_dir: str = ""
        self._theme: str = "system"
        self._initial_path: str = "/"

        self._register_ipc()

    def _register_ipc(self) -> None:
        """注册 IPC 处理器"""

        @self.ipc.on("router:ready")
        def handle_ready(window_id: int, data: str) -> int:
            logger.info("前端已就绪，导航到初始页面")
            self.go(self._initial_path)
            return 1

        @self.ipc.on("router:navigate")
        def handle_navigate(window_id: int, path: str) -> int:
            self.go(path)
            return 1

        @self.ipc.on("router:setTheme")
        def handle_set_theme(window_id: int, theme: str) -> int:
            self.set_theme(theme)
            return 1

        @self.ipc.on("router:setBackdrop")
        def handle_set_backdrop(window_id: int, backdrop: str) -> int:
            self.set_backdrop(backdrop)
            return 1

        @self.ipc.on("windowAction")
        def handle_window_action(window_id: int, action: str) -> int:
            if self._window:
                if action == "close":
                    self._window.close()
                elif action == "minimize":
                    self._window.minimize()
                elif action == "maximize":
                    self._window.maximize()
            return 1

    def page(
        self,
        path: str,
        template: str,
        title: str = "Page",
        icon: str = "",
        show_in_nav: bool = True,
    ) -> "Router":
        """注册页面"""
        self._pages.append(
            PageConfig(
                path=path,
                template=template,
                title=title,
                icon=icon,
                show_in_nav=show_in_nav,
            )
        )
        return self

    def set_theme(self, theme: str) -> None:
        """设置主题"""
        self._theme = theme.lower()
        if self._window:
            self.ipc.send(self._window.id, "router:themeChanged", theme)
            if theme.lower() == "light":
                self._window.set_theme(Theme.LIGHT)
            elif theme.lower() == "dark":
                self._window.set_theme(Theme.DARK)
            else:
                self._window.set_theme(Theme.SYSTEM)

    def set_backdrop(self, backdrop: str) -> None:
        """设置窗口背景材料

        Args:
            backdrop: mica, micaAlt, acrylic
        """
        if self._window:
            backdrop_map = {
                "mica": Backdrop.MICA,
                "micaalt": Backdrop.MICA_ALT,
                "acrylic": Backdrop.ACRYLIC,
            }
            # 支持大小写不敏感匹配
            bd = backdrop_map.get(backdrop.lower(), Backdrop.MICA)
            self._window.set_backdrop(bd)

    def mount(
        self,
        title: str = "JadeUI App",
        web_dir: str = "web",
        width: int = 1024,
        height: int = 768,
        sidebar_width: int = 220,
        theme: str = "system",
        initial_path: str = "/",
        template: Optional[str] = None,
        head_links: Optional[List[str]] = None,
        scripts: Optional[List[str]] = None,
        **window_options,
    ) -> Window:
        """挂载路由器

        Args:
            title: 窗口标题
            web_dir: 前端文件目录
            width: 窗口宽度
            height: 窗口高度
            sidebar_width: 侧边栏宽度 (仅内置模板)
            theme: 主题 (light/dark/system)
            initial_path: 初始路由路径
            template: 自定义模板文件路径 (相对于 web_dir)
                      不提供则使用内置模板
            head_links: 额外的 CSS/字体链接列表
                       例如: ["https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css"]
            scripts: 额外的 JS 脚本链接列表
                    例如: ["https://cdn.jsdelivr.net/npm/bootstrap@5/dist/js/bootstrap.bundle.min.js"]
            **window_options: 其他窗口选项
        """
        import inspect

        # 如果是相对路径，相对于调用者目录解析
        if not os.path.isabs(web_dir):
            # 遍历调用栈找到第一个不是 jadeui 包内的文件
            jadeui_dir = os.path.dirname(__file__)
            caller_dir = None
            for frame_info in inspect.stack()[1:]:
                frame_file = os.path.abspath(frame_info.filename)
                if not frame_file.startswith(jadeui_dir):
                    caller_dir = os.path.dirname(frame_file)
                    break
            if caller_dir:
                web_dir = os.path.join(caller_dir, web_dir)

        self._web_dir = os.path.abspath(web_dir)
        self._theme = theme
        self._initial_path = initial_path
        self._head_links = head_links or []
        self._scripts = scripts or []

        # 复制内置资源到用户目录
        self._copy_builtin_assets()

        # 生成或使用模板
        if template:
            # 用户自定义模板
            entry_file = template
        else:
            # 使用内置模板
            framework_html = self._generate_builtin_template(
                title, sidebar_width, self._head_links, self._scripts
            )
            entry_path = os.path.join(self._web_dir, "_app.html")
            with open(entry_path, "w", encoding="utf-8") as f:
                f.write(framework_html)
            entry_file = "_app.html"

        # 启动服务器
        url = self.server.start("router", self._web_dir)
        logger.info(f"路由器服务启动: {url}")

        # 设置窗口选项
        window_options.setdefault("remove_titlebar", True)
        window_options.setdefault("transparent", True)

        if theme.lower() == "light":
            window_options.setdefault("theme", Theme.LIGHT)
        elif theme.lower() == "dark":
            window_options.setdefault("theme", Theme.DARK)
        else:
            window_options.setdefault("theme", Theme.SYSTEM)

        # 创建窗口
        self._window = Window(
            title=title,
            width=width,
            height=height,
            url=f"{url}/{entry_file}",
            **window_options,
        )
        self._window.show()
        self._window.set_backdrop(Backdrop.MICA)

        return self._window

    def go(self, path: str) -> bool:
        """导航到指定路由"""
        page_config = self._find_page(path)
        if not page_config:
            logger.warning(f"页面未找到: {path}")
            return False

        params = self._extract_params(page_config.path, path)
        self._current_route = path

        if self._window:
            nav_data = {
                "path": path,
                "template": page_config.template,
                "title": page_config.title,
                "params": params,
            }
            self.ipc.send(self._window.id, "router:update", json.dumps(nav_data))

        return True

    def _find_page(self, path: str) -> Optional[PageConfig]:
        for page in self._pages:
            if page.path == path:
                return page
        for page in self._pages:
            if self._match_pattern(page.path, path):
                return page
        return None

    def _match_pattern(self, pattern: str, path: str) -> bool:
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        if len(pattern_parts) != len(path_parts):
            return False
        for p_part, path_part in zip(pattern_parts, path_parts):
            if p_part.startswith(":"):
                continue
            if p_part != path_part:
                return False
        return True

    def _extract_params(self, pattern: str, path: str) -> Dict[str, str]:
        params = {}
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")
        for p_part, path_part in zip(pattern_parts, path_parts):
            if p_part.startswith(":"):
                params[p_part[1:]] = path_part
        return params

    def _copy_builtin_assets(self) -> None:
        """复制内置资源到用户目录"""
        # 创建 css 目录
        css_dir = os.path.join(self._web_dir, "css")
        os.makedirs(css_dir, exist_ok=True)

        # 复制内置 CSS 到 css/jadeui.css
        src_css = os.path.join(TEMPLATES_DIR, "default.css")
        dest_css = os.path.join(css_dir, "jadeui.css")
        if os.path.exists(src_css):
            shutil.copy(src_css, dest_css)

    def _generate_builtin_template(
        self,
        title: str,
        sidebar_width: int,
        head_links: List[str],
        scripts: List[str],
    ) -> str:
        """生成内置模板"""

        nav_items = ""
        for page in self._pages:
            if page.show_in_nav:
                nav_items += f'''
                <div class="nav-item" data-path="{page.path}" onclick="router.go('{page.path}')">
                    <span class="nav-icon">{page.icon}</span>
                    <span class="nav-text">{page.title}</span>
                </div>'''

        routes_json = json.dumps(
            [{"path": p.path, "template": p.template, "title": p.title} for p in self._pages]
        )

        # 生成额外的 head 链接 (第三方库如 Bootstrap)
        extra_head_links = ""
        for link in head_links:
            if link.endswith(".css"):
                extra_head_links += f'    <link rel="stylesheet" href="{link}">\n'
            else:
                # 可能是字体或其他资源
                extra_head_links += f'    <link href="{link}" rel="stylesheet">\n'

        # 生成额外的脚本
        extra_scripts = ""
        for script in scripts:
            extra_scripts += f'    <script src="{script}"></script>\n'

        # 检测用户自定义资源
        user_css = ""
        user_js = ""

        # 检查用户 CSS 文件
        for css_path in ["css/app.css", "css/style.css", "app.css", "style.css"]:
            if os.path.exists(os.path.join(self._web_dir, css_path)):
                user_css = f'<link rel="stylesheet" href="{css_path}">'
                break

        # 检查用户 JS 文件
        for js_path in ["js/app.js", "js/main.js", "app.js", "main.js"]:
            if os.path.exists(os.path.join(self._web_dir, js_path)):
                user_js = f'<script src="{js_path}"></script>'
                break

        # 检查 favicon
        favicon_link = ""
        favicon_icon = ""
        for favicon_path in ["favicon.ico", "favicon.png", "icon.png", "icon.ico"]:
            if os.path.exists(os.path.join(self._web_dir, favicon_path)):
                favicon_link = f'<link rel="icon" href="{favicon_path}">'
                favicon_icon = f'<img src="{favicon_path}" class="titlebar-icon" alt="">'
                break

        return f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="{self._theme}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {favicon_link}
    <!-- 第三方库 -->
{extra_head_links}
    <!-- 内置样式 -->
    <link rel="stylesheet" href="css/jadeui.css">
    <!-- 用户自定义样式 (自动检测 css/app.css, css/style.css 等) -->
    {user_css}
    <style>:root {{ --sidebar-width: {sidebar_width}px; }}</style>
</head>
<body>
    <div class="titlebar">
        {favicon_icon}<span class="titlebar-title">{title}</span>
        <div class="titlebar-controls">
            <button class="titlebar-btn" onclick="windowAction('minimize')">─</button>
            <button class="titlebar-btn" onclick="windowAction('maximize')">□</button>
            <button class="titlebar-btn close" onclick="windowAction('close')">✕</button>
        </div>
    </div>

    <div class="app-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>{title}</h1>
            </div>
            <nav class="sidebar-nav">
                {nav_items}
            </nav>
            <div class="sidebar-footer">
                <div class="theme-switcher">
                    <button class="theme-btn" data-theme="light" onclick="setTheme('light')">浅色</button>
                    <button class="theme-btn" data-theme="dark" onclick="setTheme('dark')">深色</button>
                    <button class="theme-btn active" data-theme="system" onclick="setTheme('system')">自动</button>
                </div>
            </div>
        </div>

        <div class="main-content">
            <div class="content-header">
                <h2 id="page-title">加载中...</h2>
            </div>
            <div class="content-body">
                <div id="page-content" class="page-container">
                    <div class="loading">正在加载...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const routes = {routes_json};
        let currentPath = '';

        const router = {{
            go: function(path) {{ jade.ipcSend('router:navigate', path); }},
            current: function() {{ return currentPath; }},
            params: {{}},
        }};

        function windowAction(action) {{ jade.ipcSend('windowAction', action); }}

        function setTheme(theme) {{
            document.documentElement.setAttribute('data-theme', theme);
            document.querySelectorAll('.theme-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.theme === theme);
            }});
            jade.ipcSend('router:setTheme', theme);
        }}

        function setBackdrop(backdrop) {{
            jade.ipcSend('router:setBackdrop', backdrop);
        }}

        function updateNavHighlight(path) {{
            document.querySelectorAll('.nav-item').forEach(item => {{
                const itemPath = item.dataset.path;
                const isActive = itemPath === path ||
                    (path.startsWith(itemPath + '/') && itemPath !== '/') ||
                    (itemPath === '/' && path === '/');
                item.classList.toggle('active', isActive);
            }});
        }}

        async function loadTemplate(template, params) {{
            try {{
                const response = await fetch(template + '?t=' + Date.now());
                if (!response.ok) throw new Error('Template not found');
                let html = await response.text();
                for (const [key, value] of Object.entries(params)) {{
                    html = html.replace(new RegExp('\\\\{{\\\\{{' + key + '\\\\}}\\\\}}', 'g'), value);
                }}
                return html;
            }} catch (e) {{
                console.error('加载模板失败:', e);
                return '<div class="card"><p>页面加载失败</p></div>';
            }}
        }}

        jade.invoke('router:update', async function(data) {{
            try {{
                const navData = JSON.parse(data);
                currentPath = navData.path;
                router.params = navData.params || {{}};

                document.getElementById('page-title').textContent = navData.title;
                document.title = navData.title + ' - {title}';
                updateNavHighlight(navData.path);

                const content = await loadTemplate(navData.template, navData.params);
                const container = document.getElementById('page-content');
                container.innerHTML = content;

                // 重新触发动画
                container.classList.remove('page-container');
                void container.offsetWidth;
                container.classList.add('page-container');

                // 执行页面脚本
                container.querySelectorAll('script').forEach(script => {{
                    const newScript = document.createElement('script');
                    newScript.textContent = script.textContent;
                    script.parentNode.replaceChild(newScript, script);
                }});
            }} catch (e) {{
                console.error('导航失败:', e);
            }}
        }});

        jade.invoke('router:themeChanged', function(theme) {{
            document.documentElement.setAttribute('data-theme', theme.toLowerCase());
            document.querySelectorAll('.theme-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.theme === theme.toLowerCase());
            }});
        }});

        // 通知后端前端已准备好
        jade.ipcSend('router:ready', '');
    </script>
    <!-- 第三方脚本 -->
{extra_scripts}
    <!-- 用户自定义脚本 (自动检测 js/app.js, js/main.js 等) -->
    {user_js}
</body>
</html>'''

    @property
    def current_route(self) -> str:
        return self._current_route

    @property
    def window(self) -> Optional[Window]:
        return self._window
