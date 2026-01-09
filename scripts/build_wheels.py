#!/usr/bin/env python
"""
Build JadeUI wheel packages

This script builds platform-specific wheel packages containing the DLL.

Usage:
    python scripts/build_wheels.py

Build process:
    1. Auto-download DLL from GitHub releases
    2. Build platform-specific wheel packages
    3. Build source distribution

Output:
    dist/
    ├── jadeui-x.x.x-py3-none-win_amd64.whl  (64-bit Windows)
    ├── jadeui-x.x.x-py3-none-win32.whl      (32-bit Windows)
    └── jadeui-x.x.x.tar.gz                   (source)
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

# Project root directory
ROOT_DIR = Path(__file__).parent.parent
JADEUI_DIR = ROOT_DIR / "jadeui"
DLL_DIR = JADEUI_DIR / "dll"
DIST_DIR = ROOT_DIR / "dist"

# GitHub config
GITHUB_REPO = "JadeViewDocs/library"
GITHUB_RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases/download"

# 链接类型: "static" (推荐) 或 "dynamic"
LINK_TYPE = "static"


def get_dll_version() -> str:
    """Read DLL_VERSION from jadeui/downloader.py"""
    downloader_path = JADEUI_DIR / "downloader.py"
    content = downloader_path.read_text(encoding="utf-8")
    match = re.search(r'DLL_VERSION\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    raise RuntimeError("Cannot read DLL_VERSION from jadeui/downloader.py")


def get_dist_dir_name(arch: str, version: str) -> str:
    """Get distribution directory name"""
    return f"JadeView_win_{arch}_{LINK_TYPE}_v{version}"


def get_dll_filename(arch: str) -> str:
    """Get DLL filename for architecture"""
    return f"JadeView_{arch}_{LINK_TYPE}.dll"


def download_dll(arch: str, version: str) -> bool:
    """Download DLL from GitHub

    Args:
        arch: 'x64', 'x86', or 'arm64'
        version: DLL version

    Returns:
        True if successful
    """
    zip_name = f"JadeView_win_{arch}_{LINK_TYPE}_v{version}.zip"
    url = f"{GITHUB_RELEASE_URL}/v{version}/{zip_name}"
    target_dir = ROOT_DIR / get_dist_dir_name(arch, version)
    dll_name = get_dll_filename(arch)

    print(f"[*] Downloading {arch} ({LINK_TYPE}) DLL (v{version})...")
    print(f"    URL: {url}")

    try:
        # Download to temp file
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
                        bar = "#" * int(percent // 5) + "-" * (20 - int(percent // 5))
                        print(f"\r    [{bar}] {percent:.1f}%", end="", flush=True)

                print()  # newline

        # Extract to temp directory first
        temp_extract = ROOT_DIR / f"temp_extract_{arch}"
        print(f"[*] Extracting...")
        
        if temp_extract.exists():
            shutil.rmtree(temp_extract)

        with zipfile.ZipFile(tmp_path, "r") as zip_ref:
            zip_ref.extractall(temp_extract)

        # Cleanup zip file
        tmp_path.unlink()

        # Find DLL file in extracted contents
        dll_file = None
        for path in temp_extract.rglob(dll_name):
            dll_file = path
            break

        if not dll_file:
            print(f"[ERROR] DLL not found in archive: {dll_name}")
            shutil.rmtree(temp_extract)
            return False

        # Copy DLL directory contents to target
        source_dir = dll_file.parent
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        for item in source_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, target_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, target_dir / item.name)

        # Cleanup temp extract directory
        shutil.rmtree(temp_extract)

        print(f"[OK] {arch} DLL downloaded to {target_dir}")
        return True

    except urllib.error.HTTPError as e:
        print(f"\n[ERROR] Download failed: HTTP {e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\n[ERROR] Network error: {e.reason}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return False


def get_arch_config(version: str) -> dict:
    """Get architecture config with version"""
    return {
        "x64": {
            "src_dir": get_dist_dir_name("x64", version),
            "wheel_tag": "win_amd64",
            "dll_name": get_dll_filename("x64"),
        },
        "x86": {
            "src_dir": get_dist_dir_name("x86", version),
            "wheel_tag": "win32",
            "dll_name": get_dll_filename("x86"),
        },
        "arm64": {
            "src_dir": get_dist_dir_name("arm64", version),
            "wheel_tag": "win_arm64",
            "dll_name": get_dll_filename("arm64"),
        },
    }


def clean():
    """Clean build directories"""
    print("[*] Cleaning build directories...")

    # Clean dll directory
    if DLL_DIR.exists():
        shutil.rmtree(DLL_DIR)

    # Clean dist directory
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    # Clean build directory
    build_dir = ROOT_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Clean egg-info
    for p in ROOT_DIR.glob("*.egg-info"):
        shutil.rmtree(p)


def prepare_dll(arch: str, version: str) -> bool:
    """Prepare DLL files

    Args:
        arch: 'x64', 'x86', or 'arm64'
        version: DLL version

    Returns:
        True if successful
    """
    config = get_arch_config(version)[arch]
    src_dir = ROOT_DIR / config["src_dir"]

    if not src_dir.exists():
        print(f"[WARN] Not found: {src_dir}")
        print(f"       Please download and extract {config['src_dir']}.zip first")
        return False

    # Create target directory
    target_dir = DLL_DIR / config["src_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy all files
    for src_file in src_dir.iterdir():
        dst_file = target_dir / src_file.name
        if src_file.is_file():
            shutil.copy2(src_file, dst_file)
            print(f"       Copied: {src_file.name}")

    # Verify DLL exists
    dll_path = target_dir / config["dll_name"]
    if not dll_path.exists():
        print(f"[ERROR] DLL not found: {dll_path}")
        return False

    print(f"[OK] {arch} DLL prepared")
    return True


def build_wheel(arch: str, version: str) -> bool:
    """Build wheel for specific architecture

    Args:
        arch: 'x64', 'x86', or 'arm64'
        version: DLL version

    Returns:
        True if successful
    """
    config = get_arch_config(version)[arch]

    print(f"\n[*] Building {arch} wheel...")

    # Clean and prepare DLL
    if DLL_DIR.exists():
        shutil.rmtree(DLL_DIR)

    if not prepare_dll(arch, version):
        return False

    # Build wheel
    try:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("[ERROR] Build failed:")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("[ERROR] Please install build first: pip install build")
        return False

    # Rename wheel to include platform tag
    for whl in DIST_DIR.glob("jadeui-*.whl"):
        # Parse filename
        name = whl.stem
        parts = name.split("-")

        # Replace platform tag
        if len(parts) >= 5:
            parts[-1] = config["wheel_tag"]
            new_name = "-".join(parts) + ".whl"
            new_path = whl.parent / new_name

            # Delete if target exists
            if new_path.exists() and new_path != whl:
                new_path.unlink()

            whl.rename(new_path)
            print(f"[OK] Built: {new_name}")

    return True


def build_sdist() -> bool:
    """Build source distribution"""
    print("\n[*] Building source distribution...")

    # Clean DLL directory (source package doesn't include DLL)
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
            print("[ERROR] Build failed:")
            print(result.stderr)
            return False

        print("[OK] Source distribution built")
        return True

    except FileNotFoundError:
        print("[ERROR] Please install build first: pip install build")
        return False


def main():
    """Main function"""
    print("=" * 50)
    print("JadeUI Wheel Build Tool")
    print("=" * 50)

    # Get DLL version
    try:
        dll_version = get_dll_version()
        print(f"\nDLL Version: v{dll_version}")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return 1

    # Clean first (before downloading DLLs)
    clean()

    # Architectures to build (x86 is optional, uncomment if needed)
    # 构建的架构列表 (x86 可选，如需支持请取消注释)
    BUILD_ARCHS = ["x64", "arm64"]  # Add "x86" if 32-bit support needed
    
    # Check or download DLL
    arch_config = get_arch_config(dll_version)
    arch_status = {}
    
    for arch in BUILD_ARCHS:
        has_dll = (ROOT_DIR / arch_config[arch]["src_dir"]).exists()
        if not has_dll:
            print(f"\n{arch} DLL not found, downloading...")
            has_dll = download_dll(arch, dll_version)
        arch_status[arch] = has_dll

    if not any(arch_status.values()):
        print("\n[ERROR] Cannot obtain DLL files!")
        print(f"\nPlease download DLL manually (v{dll_version}):")
        print(f"  1. Visit https://github.com/{GITHUB_REPO}/releases/tag/v{dll_version}")
        print(f"  2. Download JadeView_win_x64_{LINK_TYPE}_v{dll_version}.zip etc.")
        print("  3. Extract to project root directory")
        return 1

    print("\nAvailable DLLs:")
    for arch in BUILD_ARCHS:
        if arch_status.get(arch, False):
            print(f"  [OK] {arch} ({arch_config[arch]['src_dir']})")
        else:
            print(f"  [--] {arch} not found")

    # Ensure dist directory exists
    DIST_DIR.mkdir(exist_ok=True)

    # Build wheels
    success = True

    for arch in BUILD_ARCHS:
        if arch_status.get(arch, False):
            if not build_wheel(arch, dll_version):
                success = False

    # Build source distribution
    if not build_sdist():
        success = False

    # Clean DLL directory
    if DLL_DIR.exists():
        shutil.rmtree(DLL_DIR)

    # Result
    print("\n" + "=" * 50)
    if success:
        print("[SUCCESS] Build completed!")
        print(f"\nOutput directory: {DIST_DIR}")
        for f in sorted(DIST_DIR.iterdir()):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  - {f.name} ({size_mb:.1f} MB)")

        print("\nUpload to PyPI:")
        print("  twine upload dist/*")

        print("\nUpload to TestPyPI:")
        print("  twine upload --repository testpypi dist/*")
    else:
        print("[FAILED] Build failed, please check error messages")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
