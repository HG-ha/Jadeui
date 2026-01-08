#!/usr/bin/env python
"""
构建 JadeUI wheel 包

此脚本用于构建包含 DLL 的平台特定 wheel 包。

使用方法:
    python scripts/build_wheels.py

构建流程:
    1. 自动从 GitHub 下载对应版本的 DLL
    2. 构建平台特定的 wheel 包
    3. 构建源码包

构建输出:
    dist/
    ├── jadeui-x.x.x-py3-none-win_amd64.whl  (64位 Windows)
    ├── jadeui-x.x.x-py3-none-win32.whl      (32位 Windows)
    └── jadeui-x.x.x.tar.gz                   (源码包)
"""

import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
JADEUI_DIR = ROOT_DIR / "jadeui"
DLL_DIR = JADEUI_DIR / "dll"
DIST_DIR = ROOT_DIR / "dist"

# GitHub 配置
GITHUB_REPO = "JadeViewDocs/library"
GITHUB_RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases/download"


def get_dll_version() -> str:
    """从 jadeui/downloader.py 读取 DLL_VERSION"""
    downloader_path = JADEUI_DIR / "downloader.py"
    content = downloader_path.read_text(encoding="utf-8")
    match = re.search(r'DLL_VERSION\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    raise RuntimeError("无法从 jadeui/downloader.py 读取 DLL_VERSION")


def download_dll(arch: str, version: str) -> bool:
    """从 GitHub 下载 DLL

    Args:
        arch: 'x64' 或 'x86'
        version: DLL 版本号

    Returns:
        成功返回 True
    """
    zip_name = f"JadeView-dist_{arch}.zip"
    url = f"{GITHUB_RELEASE_URL}/v{version}/{zip_name}"
    target_dir = ROOT_DIR / f"JadeView-dist_{arch}"

    print(f"⬇️  下载 {arch} DLL (v{version})...")
    print(f"   URL: {url}")

    try:
        # 下载到临时文件
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)

            request = urllib.request.Request(
                url, headers={"User-Agent": f"jadeui-build/{version}"}
            )

            with urllib.request.urlopen(request, timeout=60) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    tmp_file.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        bar = "█" * int(percent // 5) + "░" * (20 - int(percent // 5))
                        print(f"\r   [{bar}] {percent:.1f}%", end="", flush=True)

                print()  # 换行

        # 解压
        print(f"📂 解压到 {target_dir}...")
        if target_dir.exists():
            shutil.rmtree(target_dir)

        with zipfile.ZipFile(tmp_path, "r") as zip_ref:
            zip_ref.extractall(ROOT_DIR)

        # 清理临时文件
        tmp_path.unlink()

        print(f"✅ {arch} DLL 下载完成")
        return True

    except urllib.error.HTTPError as e:
        print(f"\n❌ 下载失败: HTTP {e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\n❌ 网络错误: {e.reason}")
        return False
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return False


# 架构配置
ARCH_CONFIG = {
    "x64": {
        "src_dir": "JadeView-dist_x64",
        "wheel_tag": "win_amd64",
        "dll_name": "JadeView_x64.dll",
    },
    "x86": {
        "src_dir": "JadeView-dist_x86",
        "wheel_tag": "win32",
        "dll_name": "JadeView.dll",
    },
}


def clean():
    """清理构建目录"""
    print("🧹 清理构建目录...")

    # 清理 dll 目录
    if DLL_DIR.exists():
        shutil.rmtree(DLL_DIR)

    # 清理 dist 目录
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    # 清理 build 目录
    build_dir = ROOT_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # 清理 egg-info
    for p in ROOT_DIR.glob("*.egg-info"):
        shutil.rmtree(p)


def prepare_dll(arch: str) -> bool:
    """准备 DLL 文件

    Args:
        arch: 'x64' 或 'x86'

    Returns:
        成功返回 True
    """
    config = ARCH_CONFIG[arch]
    src_dir = ROOT_DIR / config["src_dir"]

    if not src_dir.exists():
        print(f"⚠️  未找到 {src_dir}")
        print(f"   请先下载并解压 {config['src_dir']}.zip")
        return False

    # 创建目标目录
    target_dir = DLL_DIR / config["src_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)

    # 复制所有文件
    for src_file in src_dir.iterdir():
        dst_file = target_dir / src_file.name
        if src_file.is_file():
            shutil.copy2(src_file, dst_file)
            print(f"   复制: {src_file.name}")

    # 验证 DLL 存在
    dll_path = target_dir / config["dll_name"]
    if not dll_path.exists():
        print(f"❌ 未找到 DLL: {dll_path}")
        return False

    print(f"✅ {arch} DLL 准备完成")
    return True


def build_wheel(arch: str) -> bool:
    """构建特定架构的 wheel

    Args:
        arch: 'x64' 或 'x86'

    Returns:
        成功返回 True
    """
    config = ARCH_CONFIG[arch]

    print(f"\n📦 构建 {arch} wheel...")

    # 清理并准备 DLL
    if DLL_DIR.exists():
        shutil.rmtree(DLL_DIR)

    if not prepare_dll(arch):
        return False

    # 构建 wheel
    try:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("❌ 构建失败:")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("❌ 请先安装 build: pip install build")
        return False

    # 重命名 wheel 以包含平台标签
    for whl in DIST_DIR.glob("jadeui-*.whl"):
        # 解析文件名
        name = whl.stem
        parts = name.split("-")

        # 替换平台标签
        if len(parts) >= 5:
            parts[-1] = config["wheel_tag"]
            new_name = "-".join(parts) + ".whl"
            new_path = whl.parent / new_name

            # 如果目标已存在，先删除
            if new_path.exists() and new_path != whl:
                new_path.unlink()

            whl.rename(new_path)
            print(f"✅ 构建完成: {new_name}")

    return True


def build_sdist() -> bool:
    """构建源码包"""
    print("\n📦 构建源码包...")

    # 清理 DLL 目录（源码包不包含 DLL）
    if DLL_DIR.exists():
        shutil.rmtree(DLL_DIR)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--sdist"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("❌ 构建失败:")
            print(result.stderr)
            return False

        print("✅ 源码包构建完成")
        return True

    except FileNotFoundError:
        print("❌ 请先安装 build: pip install build")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("JadeUI Wheel 构建工具")
    print("=" * 50)

    # 获取 DLL 版本
    try:
        dll_version = get_dll_version()
        print(f"\nDLL 版本: v{dll_version}")
    except Exception as e:
        print(f"\n❌ {e}")
        return 1

    # 检查或下载 DLL
    has_x64 = (ROOT_DIR / "JadeView-dist_x64").exists()
    has_x86 = (ROOT_DIR / "JadeView-dist_x86").exists()

    if not has_x64:
        print("\n未找到 x64 DLL，正在下载...")
        has_x64 = download_dll("x64", dll_version)

    if not has_x86:
        print("\n未找到 x86 DLL，正在下载...")
        has_x86 = download_dll("x86", dll_version)

    if not has_x64 and not has_x86:
        print("\n❌ 无法获取 DLL 文件!")
        print(f"\n请手动下载 DLL (v{dll_version}):")
        print(f"  1. 访问 https://github.com/{GITHUB_REPO}/releases/tag/v{dll_version}")
        print("  2. 下载 JadeView-dist_x64.zip 和/或 JadeView-dist_x86.zip")
        print("  3. 解压到项目根目录")
        return 1

    print("\n可用的 DLL:")
    if has_x64:
        print("  ✅ x64 (JadeView-dist_x64)")
    else:
        print("  ⚠️  x64 未找到")

    if has_x86:
        print("  ✅ x86 (JadeView-dist_x86)")
    else:
        print("  ⚠️  x86 未找到")

    # 清理
    clean()

    # 确保 dist 目录存在
    DIST_DIR.mkdir(exist_ok=True)

    # 构建 wheels
    success = True

    if has_x64:
        if not build_wheel("x64"):
            success = False

    if has_x86:
        if not build_wheel("x86"):
            success = False

    # 构建源码包
    if not build_sdist():
        success = False

    # 清理 DLL 目录
    if DLL_DIR.exists():
        shutil.rmtree(DLL_DIR)

    # 结果
    print("\n" + "=" * 50)
    if success:
        print("🎉 构建完成!")
        print(f"\n输出目录: {DIST_DIR}")
        for f in sorted(DIST_DIR.iterdir()):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  - {f.name} ({size_mb:.1f} MB)")

        print("\n上传到 PyPI:")
        print("  twine upload dist/*")

        print("\n上传到 TestPyPI:")
        print("  twine upload --repository testpypi dist/*")
    else:
        print("❌ 构建失败，请检查错误信息")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

