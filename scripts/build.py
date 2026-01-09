#!/usr/bin/env python
"""
JadeUI 应用打包脚本
使用 Nuitka 将 Python 应用打包成独立的可执行文件

为什么使用 Nuitka 4.0rc7?
- Nuitka 官方稳定版 (2.x/3.x) 的 onefile 模式存在 bug，没有正确打包 VC++ 运行时
- 导致生成的 exe 在纯净 Windows 系统上无法运行（缺少 vcruntime140.dll）
- Nuitka 4.0 测试版修复了此问题，onefile bootstrap 使用静态链接
- 安装方式: pip install jadeui[dev] 会自动从仓库下载 nuitka-4.0.rc7.zip
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path


def get_jadeui_dll_path() -> Path | None:
    """
    查找 jadeui 库的 DLL 目录

    Returns:
        DLL 目录路径，如果未找到返回 None
    """
    # 尝试使用 jadeui.downloader 模块
    try:
        from jadeui.downloader import find_dll

        dll_path = find_dll()
        if dll_path:
            return dll_path.parent
    except ImportError:
        pass

    # 回退：手动确定架构和目录
    arch = "x64" if platform.machine().endswith("64") else "x86"
    # 新格式: JadeView_win_{arch}_static_v{version}
    # 由于不知道确切版本，尝试查找匹配的目录
    
    def find_matching_dir(base_path: Path) -> Path | None:
        """查找匹配的 DLL 目录"""
        if not base_path.exists():
            return None
        # 优先查找新格式目录
        for pattern in [f"JadeView_win_{arch}_static_*", f"JadeView_win_{arch}_dynamic_*"]:
            matches = list(base_path.glob(pattern))
            if matches:
                # 返回最新版本（按名称排序）
                return sorted(matches)[-1]
        return None

    # 尝试从已安装的 jadeui 包中查找
    try:
        import jadeui

        package_path = Path(jadeui.__file__).parent
        for subdir in ["dll", "lib"]:
            dll_dir = find_matching_dir(package_path / subdir)
            if dll_dir:
                return dll_dir
    except ImportError:
        pass

    # 尝试从当前项目中查找（开发模式）
    search_bases = [
        Path.cwd() / "jadeui" / "dll",
        Path.cwd() / "jadeui" / "lib",
        Path.cwd() / "lib",
        Path(__file__).parent.parent / "jadeui" / "dll",
        Path(__file__).parent.parent / "jadeui" / "lib",
        Path(__file__).parent.parent / "lib",
        Path.cwd(),
    ]

    for base in search_bases:
        dll_dir = find_matching_dir(base)
        if dll_dir:
            return dll_dir

    return None


def get_jadeui_dll_files(dll_dir: Path) -> list[tuple[Path, str]]:
    """
    获取 DLL 目录中所有需要包含的文件

    Args:
        dll_dir: DLL 目录路径

    Returns:
        文件路径和目标路径的元组列表
    """
    files = []
    dest_dir = dll_dir.name  # 如 "JadeView_win_x64_static_v0.1.2"

    # 包含目录中的所有文件
    for file_path in dll_dir.iterdir():
        if file_path.is_file():
            # 格式: 源文件=目标文件
            dest_path = f"{dest_dir}/{file_path.name}"
            files.append((file_path, dest_path))

    return files


def build(
    source_file: str,
    icon: str | None = None,
    output_name: str | None = None,
    output_dir: str = "dist",
    include_data_dirs: list[str] | None = None,
    include_data_files: list[str] | None = None,
    show_console: bool = False,
    use_upx: bool = False,
    include_jadeui_dll: bool = True,
    compression_level: int = 1,
    onefile: bool = True,
) -> int:
    """
    使用 Nuitka 打包 Python 应用

    Args:
        source_file: 要编译的 Python 文件
        icon: 图标文件路径 (.ico 或 .png)
        output_name: 输出的可执行文件名（不含扩展名）
        output_dir: 输出目录
        include_data_dirs: 要包含的数据目录列表，格式为 "src=dest"
        include_data_files: 要包含的数据文件列表，格式为 "src=dest"
        show_console: 是否显示控制台窗口
        use_upx: 是否使用 UPX 压缩
        include_jadeui_dll: 是否自动包含 jadeui DLL
        compression_level: 压缩级别 0-3（0=不压缩, 1=基础, 2=中等, 3=最大压缩）
        onefile: 是否打包为单个可执行文件（默认 True）

    Returns:
        子进程的返回码
    """
    source_path = Path(source_file)
    if not source_path.exists():
        print(f"错误: 源文件不存在: {source_file}")
        return 1

    # 源文件所在目录
    source_dir = source_path.parent

    # 默认输出文件名为源文件名（不含扩展名）
    if output_name is None:
        output_name = source_path.stem

    # 初始化数据目录和文件列表
    data_dirs = list(include_data_dirs) if include_data_dirs else []
    data_files = list(include_data_files) if include_data_files else []

    # 默认包含 web 目录（如果存在）
    web_dir = source_dir / "web"
    if web_dir.exists() and web_dir.is_dir():
        # 检查是否已经手动添加了 web 目录
        has_web_dir = any("web=" in d or d.startswith("web=") for d in data_dirs)
        if not has_web_dir:
            data_dirs.append(f"{web_dir}=web")
            print(f"✅ 自动包含 web 目录: {web_dir}")

    # 默认使用 web/favicon.png 作为图标（如果存在且未指定图标）
    if icon is None:
        default_icon = source_dir / "web" / "favicon.png"
        if default_icon.exists():
            icon = str(default_icon)
            print(f"✅ 自动使用图标: {icon}")

    # 自动包含 jadeui DLL
    jadeui_dll_path = None
    jadeui_dll_files: list[tuple[Path, str]] = []
    if include_jadeui_dll:
        jadeui_dll_path = get_jadeui_dll_path()
        if jadeui_dll_path:
            # 获取所有需要包含的文件
            jadeui_dll_files = get_jadeui_dll_files(jadeui_dll_path)
            print(f"✅ 找到 JadeUI DLL 目录: {jadeui_dll_path}")
            for src, dest in jadeui_dll_files:
                print(f"   📦 {src.name} -> {dest}")
        else:
            print("⚠️  警告: 未找到 JadeUI DLL，打包后的程序可能无法运行")
            print("   请确保已安装 jadeui 库或 DLL 文件存在")


    # 构建 Nuitka 命令
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        f"--output-dir={output_dir}",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--show-progress",
        # 排除不必要的模块
        "--nofollow-import-to=pytest,unittest,setuptools,pip,wheel,distutils",
    ]

    # 单文件模式
    if onefile:
        cmd.append("--onefile")
        cmd.append(f"--output-filename={output_name}.exe")

    # 根据压缩级别添加优化选项
    if compression_level >= 1:
        # 级别1: 基础优化
        cmd.append("--lto=yes")  # 链接时优化

    if compression_level >= 2:
        # 级别2: 中等压缩
        cmd.append("--python-flag=no_docstrings")  # 移除文档字符串
        cmd.append("--python-flag=no_asserts")  # 移除 assert 语句
        # Nuitka onefile 默认已启用压缩，无需额外选项

    if compression_level >= 3:
        # 级别3: 最大压缩
        cmd.append("--python-flag=-OO")  # Python 最高优化级别

    # Windows 控制台设置
    if sys.platform == "win32":
        if not show_console:
            cmd.append("--windows-disable-console")
            cmd.append("--disable-console")

        # 图标设置
        if icon:
            icon_path = Path(icon)
            if not icon_path.exists():
                print(f"警告: 图标文件不存在: {icon}")
            else:
                cmd.append(f"--windows-icon-from-ico={icon}")

    # UPX 压缩（在 onefile 模式下压缩内部 DLL）
    if use_upx:
        cmd.append("--enable-plugin=upx")

    # 包含数据目录
    for data_dir in data_dirs:
        cmd.append(f"--include-data-dir={data_dir}")

    # 包含数据文件
    for data_file in data_files:
        cmd.append(f"--include-data-files={data_file}")

    # 包含 JadeUI DLL 文件
    for src, dest in jadeui_dll_files:
        cmd.append(f"--include-data-files={src}={dest}")

    # 添加源文件
    cmd.append(source_file)

    # 压缩级别描述
    compression_desc = {
        0: "不压缩",
        1: "基础优化 (LTO)",
        2: "中等压缩 (LTO + 无文档/断言)",
        3: "最大压缩 (LTO + 无文档/断言 + -OO)",
    }

    print("=" * 60)
    print("JadeUI 应用打包")
    print("=" * 60)
    print(f"源文件: {source_file}")
    print(f"输出目录: {output_dir}")
    if onefile:
        print(f"输出文件: {output_name}.exe")
    else:
        print(f"输出目录: {output_dir}/{output_name}.dist/")
    print(f"打包模式: {'单文件 (onefile)' if onefile else '目录 (standalone)'}")
    print(f"压缩级别: {compression_level} - {compression_desc.get(compression_level, '未知')}")
    if icon:
        print(f"图标: {icon}")
    if jadeui_dll_files:
        print(f"JadeUI DLL: {len(jadeui_dll_files)} 个文件")
    if data_dirs:
        print(f"数据目录: {data_dirs}")
    if data_files:
        print(f"数据文件: {data_files}")
    print("=" * 60)
    print("执行命令:")
    print(" ".join(cmd))
    print("=" * 60)

    # 执行打包命令
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="JadeUI 应用打包工具 - 使用 Nuitka 打包 Python 应用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build.py app.py                    # 最简单的打包（默认单文件+压缩级别1）
  python build.py app.py -c 2               # 中等压缩（推荐）
  python build.py app.py -c 3               # 最大压缩
  python build.py app.py --output MyApp     # 指定输出文件名
  python build.py app.py --icon custom.ico  # 使用自定义图标
  python build.py app.py --no-onefile       # 打包为目录而非单文件
  python build.py app.py --include-data-dir assets=assets  # 添加额外目录

压缩级别说明:
  0 - 不压缩：最快编译，最大体积
  1 - 基础优化：启用 LTO 链接时优化（默认）
  2 - 中等压缩：LTO + 移除文档字符串和 assert 语句
  3 - 最大压缩：全部优化 + Python -OO 模式

默认行为:
  - 自动包含 JadeUI DLL 文件
  - 自动包含 web 目录（如果存在）
  - 自动使用 web/favicon.png 作为图标（如果存在）
        """,
    )

    parser.add_argument("source", help="要编译的 Python 源文件")

    parser.add_argument(
        "-i",
        "--icon",
        help="应用程序图标文件 (.ico 或 .png)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="输出的可执行文件名（不含 .exe 扩展名）",
    )

    parser.add_argument(
        "--output-dir",
        default="dist",
        help="输出目录（默认: dist）",
    )

    parser.add_argument(
        "--include-data-dir",
        action="append",
        dest="data_dirs",
        metavar="SRC=DEST",
        help="包含数据目录，格式: 源目录=目标目录（可多次使用）",
    )

    parser.add_argument(
        "--include-data-file",
        action="append",
        dest="data_files",
        metavar="SRC=DEST",
        help="包含数据文件，格式: 源文件=目标文件（可多次使用）",
    )

    parser.add_argument(
        "--console",
        action="store_true",
        help="显示控制台窗口（默认隐藏）",
    )

    parser.add_argument(
        "--upx",
        action="store_true",
        help="启用 UPX 压缩（默认禁用）",
    )

    parser.add_argument(
        "--no-jadeui-dll",
        action="store_true",
        help="不自动包含 JadeUI DLL（默认自动包含）",
    )

    parser.add_argument(
        "-c",
        "--compress",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
        metavar="LEVEL",
        help="压缩级别 0-3（0=不压缩, 1=基础LTO, 2=移除文档/断言, 3=最大压缩+UPX）默认: 1",
    )

    parser.add_argument(
        "--no-onefile",
        action="store_true",
        help="不打包为单个可执行文件，而是生成目录（默认打包为单文件）",
    )

    args = parser.parse_args()

    result = build(
        source_file=args.source,
        icon=args.icon,
        output_name=args.output,
        output_dir=args.output_dir,
        include_data_dirs=args.data_dirs,
        include_data_files=args.data_files,
        show_console=args.console,
        use_upx=args.upx,
        include_jadeui_dll=not args.no_jadeui_dll,
        compression_level=args.compress,
        onefile=not args.no_onefile,
    )

    sys.exit(result)


if __name__ == "__main__":
    main()
