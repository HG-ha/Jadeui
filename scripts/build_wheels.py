#!/usr/bin/env python
"""
构建 JadeUI wheel 包

此脚本用于构建包含 DLL 的平台特定 wheel 包。

使用方法:
    python scripts/build_wheels.py

构建前准备:
    1. 下载对应架构的 DLL 压缩包:
       - JadeView-dist_x64.zip (64位)
       - JadeView-dist_x86.zip (32位)
    
    2. 解压到项目根目录:
       - JadeView-dist_x64/
       - JadeView-dist_x86/

构建输出:
    dist/
    ├── jadeui-0.1.0-py3-none-win_amd64.whl  (64位 Windows)
    ├── jadeui-0.1.0-py3-none-win32.whl      (32位 Windows)
    └── jadeui-0.1.0.tar.gz                   (源码包)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
JADEUI_DIR = ROOT_DIR / "jadeui"
DLL_DIR = JADEUI_DIR / "dll"
DIST_DIR = ROOT_DIR / "dist"

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
            print(f"❌ 构建失败:")
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
            print(f"❌ 构建失败:")
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
    
    # 检查 DLL 目录
    has_x64 = (ROOT_DIR / "JadeView-dist_x64").exists()
    has_x86 = (ROOT_DIR / "JadeView-dist_x86").exists()
    
    if not has_x64 and not has_x86:
        print("\n❌ 未找到 DLL 文件!")
        print("\n请先下载 DLL:")
        print("  1. 访问 https://github.com/JadeViewDocs/library/releases")
        print("  2. 下载 JadeView-dist_x64.zip 和/或 JadeView-dist_x86.zip")
        print("  3. 解压到项目根目录")
        return 1
    
    print(f"\n检测到的 DLL:")
    if has_x64:
        print(f"  ✅ x64 (JadeView-dist_x64)")
    else:
        print(f"  ⚠️  x64 未找到")
    
    if has_x86:
        print(f"  ✅ x86 (JadeView-dist_x86)")
    else:
        print(f"  ⚠️  x86 未找到")
    
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

