#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kubernetes 集群巡检报告分析执行页面 - 入口页
"""
# 核心公共导入
import streamlit as st
from pathlib import Path
import sys

# ===================== 页面基础配置=====================

# 设置页面配置 - 必须是第一个Streamlit命令
st.set_page_config(
    page_title="集群巡检报告分析 - kubeeye",
    page_icon="🔍",
    layout="wide"
)

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.common import initialize_page

initialize_page(
    title="集群巡检报告分析",
    icon="📋",
    page_title="集群巡检报告分析中心",
    page_subtitle="分析和可视化Kubernetes集群巡检报告，帮助识别问题并支持AI提供解决建议。"
)

# ===================== 导入拆分后的所有模块 =====================
from components.report_analysis import (
    handle_import, display_reports_overview,
    display_report_operations, display_report_detail
)
from components.report_analysis.ai_analysis import render_ai_tab

# ===================== 初始化会话状态（原文件保留，无修改）=====================
if 'view_mode_analysis' not in st.session_state:
    st.session_state.view_mode_analysis = "list"
if 'selected_report_id_analysis' not in st.session_state:
    st.session_state.selected_report_id_analysis = None
if "import_mode" not in st.session_state:
    st.session_state.import_mode = "file"

# ===================== 原文件标签页结构（无任何修改）=====================
tab1, tab2, tab3 = st.tabs(["导入报告", "报告分析", "AI分析"])

with tab1:
    st.markdown("将已有的 Kubernetes 集群巡检报告导入系统进行查看和分析。")
    st.radio(
        "选择导入方式",
        ["file", "text"],
        format_func=lambda x: "文件上传" if x == "file" else "文本输入",
        key="import_mode",
        horizontal=True
    )
    with st.form("import_report_form", clear_on_submit=False):
        uploaded_file = st.file_uploader(
            "上传 JSON 文件",
            type=["json"],
            key="uploaded_file",
            disabled=st.session_state.import_mode != "file"
        )
        text_data = st.text_area(
            "输入 JSON 文本",
            height=300,
            key="text_area_data",
            disabled=st.session_state.import_mode != "text"
        )
        submitted = st.form_submit_button(
            "导入报告",
            use_container_width=True,
            type="primary"
        )
        if submitted:
            handle_import(
                st.session_state.import_mode,
                uploaded_file,
                text_data
            )

with tab2:
    # 根据视图模式显示不同内容
    if st.session_state.view_mode_analysis == "list":
        display_reports_overview()
    elif st.session_state.view_mode_analysis == "operations":
        if st.session_state.selected_report_id_analysis:
            display_report_operations(st.session_state.selected_report_id_analysis)
        else:
            st.error("❌ 未选择报告")
            st.session_state.view_mode_analysis = "list"
            st.rerun()
    elif st.session_state.view_mode_analysis == "detail":
        if st.session_state.selected_report_id_analysis:
            display_report_detail(st.session_state.selected_report_id_analysis)
        else:
            st.error("❌ 未选择报告")
            st.session_state.view_mode_analysis = "list"
            st.rerun()

with tab3:
    # 调用AI分析模块的渲染函数
    render_ai_tab()