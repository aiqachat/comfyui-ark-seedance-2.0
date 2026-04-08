"""
测试脚本 - 验证项目结构和配置
"""

import sys
from pathlib import Path


def test_project_structure():
    """测试项目结构"""
    print("测试项目结构...")

    required_files = [
        "__init__.py",
        "config.py",
        "seedance_client.py",
        "Ark_seedance.py",
        "Ark_seedance_query.py",
        "Ark_seedance_utils.py",
        "requirements.txt",
        "README.md",
        "web/ark_seedance_ui.js",
        "web/ark_seedance_tutorials.js",
    ]

    all_exist = True
    for file in required_files:
        path = Path(__file__).parent / file
        if path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} 不存在")
            all_exist = False

    return all_exist


def test_config():
    """测试配置模块"""
    print("\n测试配置模块...")

    try:
        from config import load_config, get_api_base_url, get_poll_interval

        config = load_config()
        print(f"  ✓ 配置文件加载成功")
        print(f"    API Base URL: {get_api_base_url()}")
        print(f"    Poll Interval: {get_poll_interval()}秒")
        return True
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        return False


def test_client_basic():
    """测试客户端基本功能（不需要 torch）"""
    print("\n测试客户端基本功能...")

    try:
        from seedance_client import SeedanceClient

        # 测试 content 构建
        content = SeedanceClient.build_content(text="测试提示词")
        assert len(content) == 1
        assert content[0]["type"] == "text"
        print(f"  ✓ Content 构建成功")

        # 测试 image_to_base64
        from PIL import Image
        import numpy as np

        test_img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        b64 = SeedanceClient.image_to_base64(test_img)
        assert b64.startswith("data:image/png;base64,")
        print(f"  ✓ Image to Base64 转换成功")

        return True
    except Exception as e:
        print(f"  ✗ 客户端测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Ark Seedance 2.0 - 项目测试")
    print("=" * 60)

    all_passed = True

    all_passed &= test_project_structure()
    all_passed &= test_config()
    all_passed &= test_client_basic()

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！")
        print("\n下一步:")
        print("1. 编辑 master_key.ini 配置 API Key")
        print("2. 将本项目复制到 ComfyUI/custom_nodes 目录")
        print("3. 安装依赖: pip install -r requirements.txt")
        print("4. 重启 ComfyUI")
    else:
        print("✗ 部分测试失败，请检查错误信息")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
