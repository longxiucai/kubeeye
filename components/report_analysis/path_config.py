#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告分析模块 - 路径配置（所有路径常量唯一源头）
"""
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
# 把项目根目录加入sys.path（保证跨模块导入正常）
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 核心数据目录、报告目录常量
DATA_DIR = ROOT_DIR / "data"
RESULTS_DIR = DATA_DIR / "results" / "analysis_reports"

# ===================== 目录初始化（确保目录存在）=====================
def init_dirs():
    """初始化所需目录（确保analysis_reports目录存在）"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 模块加载时自动初始化目录
init_dirs()

# 导出所有常量和函数（供其他子模块导入）
__all__ = ["ROOT_DIR", "DATA_DIR", "RESULTS_DIR", "init_dirs"]