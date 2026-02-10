#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告分析模块包初始化 - 导出所有子模块函数
"""
# 从数据操作模块导出
from .data_operations import (
    list_clusters, list_results, load_result, delete_report,
    parse_inspection_metrics, handle_import
)

# 从页面展示模块导出
from .page_display import (
    display_reports_overview, display_statistics_overview,
    display_reports_table, display_report_operations,
    display_report_detail, display_inspection_items,
    display_items_list, safe_display_opa_violations_table
)

# 从图表可视化模块导出
from .chart_visualization import (
    display_reports_analysis, display_node_metrics,
    display_prom_metrics, display_opa_metrics,
    STATUS_COLOR_MAP, DEFAULT_STATUS_COLOR, COLOR_POOL,
    color_cycle, COLOR_MAP, mpl_color_to_plotly, get_color_by_line_key
)

# 从AI分析模块导出
from .ai_analysis import (
    display_ai_analysis_results, ai_generate, normalize
)

# 导出所有常量，保持全局可访问
__all__ = [
    # 数据操作
    "list_clusters", "list_results", "load_result", "delete_report",
    "parse_inspection_metrics", "handle_import",
    # 页面展示
    "display_reports_overview", "display_statistics_overview",
    "display_reports_table", "display_report_operations",
    "display_report_detail", "display_inspection_items",
    "display_items_list", "safe_display_opa_violations_table",
    # 图表可视化
    "display_reports_analysis", "display_node_metrics",
    "display_prom_metrics", "display_opa_metrics",
    "STATUS_COLOR_MAP", "DEFAULT_STATUS_COLOR", "COLOR_POOL",
    "color_cycle", "COLOR_MAP", "mpl_color_to_plotly", "get_color_by_line_key",
    # AI分析
    "display_ai_analysis_results", "ai_generate", "normalize"
]