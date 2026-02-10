#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告分析-页面展示模块：概览/操作/详情页、报告表格、检查项展示
"""
from pathlib import Path
import sys
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# 导入项目组件
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from components.ui.result_display import display_opa_violations_table


def safe_display_opa_violations_table(violations_data, show_expander=False, table_key=None):
    """安全调用OPA违规表格"""
    try:
        if table_key:
            return display_opa_violations_table(violations_data, show_expander=show_expander, table_key=table_key)
        else:
            return display_opa_violations_table(violations_data, show_expander=show_expander)
    except TypeError:
        return display_opa_violations_table(violations_data, show_expander=show_expander)


def display_reports_overview():
    """显示报告概览页面"""
    from .data_operations import list_clusters, list_results  # 内部依赖导入
    st.markdown("查看和管理所有集群的巡检报告，快速识别问题并获取解决建议。")
    clusters = list_clusters()
    all_results = list_results()
    if not all_results:
        st.info("📭 暂无巡检报告。请先执行巡检任务生成报告。")
        if st.button("🚀 去执行巡检", type="primary"):
            st.switch_page("pages/2_cluster_inspect.py")
        return
    # 过滤控制
    st.markdown("### 🔍 筛选报告")
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_cluster = st.selectbox("选择集群", ["全部"] + clusters, help="筛选特定集群的报告")
    with col2:
        inspection_types = ["全部", "immediate", "scheduled"]
        selected_type = st.selectbox("巡检类型", inspection_types, format_func=lambda x: "立即巡检" if x == "immediate" else ("定时巡检" if x == "scheduled" else x))
    with col3:
        date_filter = st.selectbox("时间范围", ["全部", "今天", "最近7天", "最近30天"])
    # 应用筛选
    filtered_results = all_results
    if selected_cluster != "全部":
        filtered_results = [r for r in filtered_results if r["cluster_name"] == selected_cluster]
    if selected_type != "全部":
        filtered_results = [r for r in filtered_results if r["inspection_type"] == selected_type]
    if date_filter != "全部":
        now = datetime.now()
        if date_filter == "今天":
            filtered_results = [r for r in filtered_results if datetime.fromisoformat(r['timestamp']).date() == now.date()]
        elif date_filter == "最近7天":
            week_ago = now - timedelta(days=7)
            filtered_results = [r for r in filtered_results if datetime.fromisoformat(r['timestamp']) >= week_ago]
        elif date_filter == "最近30天":
            month_ago = now - timedelta(days=30)
            filtered_results = [r for r in filtered_results if datetime.fromisoformat(r['timestamp']) >= month_ago]
    # 显示统计和表格
    if filtered_results:
        display_statistics_overview(filtered_results)
        display_reports_table(filtered_results)
        from .chart_visualization import display_reports_analysis  # 内部依赖导入
        display_reports_analysis(filtered_results)
    else:
        st.info("🔍 没有找到符合条件的巡检报告")


def display_statistics_overview(filtered_results):
    """显示统计概览"""
    st.markdown("### 📈 统计概览")
    total_reports = len(filtered_results)
    total_exceptions = sum(r['critical'] + r['warning'] for r in filtered_results)
    total_passed = sum(r['passed'] for r in filtered_results)
    latest_report = max(filtered_results, key=lambda x: x['timestamp'])
    latest_time = datetime.fromisoformat(latest_report['timestamp']).strftime('%m-%d %H:%M')
    # 指标卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 报告总数", total_reports)
    with col2:
        st.metric("⚠️ 异常", total_exceptions)
    with col3:
        st.metric("✅ 通过", total_passed)
    with col4:
        st.metric("🕒 最新报告", latest_time)


def display_reports_table(filtered_results):
    """显示报告列表"""
    st.markdown("### 📋 报告列表")
    st.markdown("*点击报告ID左侧空白单元格查看详情和进行操作*")
    if not filtered_results:
        st.info("📭 暂无符合条件的报告")
        return
    # 排序
    sorted_results = sorted(filtered_results, key=lambda x: (-(x['critical'] + x['warning']), x['timestamp']), reverse=True)
    # 构造DataFrame
    df_data = []
    for result in sorted_results:
        timestamp = datetime.fromisoformat(result['timestamp'])
        total_exceptions = result['critical'] + result['warning']
        report_id = result['result_id']
        df_data.append({
            "📄 报告ID": report_id,
            "🏢 集群": result['cluster_name'],
            "⏰ 巡检时间": timestamp.strftime('%m-%d %H:%M'),
            "🔄 类型": "⚡ 立即" if result['inspection_type'] == 'immediate' else "⏲️ 定时",
            "📊 状态": "🔴 异常" if total_exceptions > 0 else "🟢 正常",
            "⚠️ 异常": total_exceptions,
            "✅ 通过": result['passed'],
            "📈 总计": total_exceptions + result['passed']
        })
    df = pd.DataFrame(df_data)
    # 数据表格
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "📄 报告ID": st.column_config.TextColumn("📄 报告ID", help="点击行查看详情和操作"),
            "🏢 集群": st.column_config.TextColumn("🏢 集群"),
            "⏰ 巡检时间": st.column_config.TextColumn("⏰ 巡检时间"),
            "🔄 类型": st.column_config.TextColumn("🔄 类型"),
            "📊 状态": st.column_config.TextColumn("📊 状态"),
            "⚠️ 异常": st.column_config.NumberColumn("⚠️ 异常"),
            "✅ 通过": st.column_config.NumberColumn("✅ 通过"),
            "📈 总计": st.column_config.NumberColumn("📈 总计")
        }
    )
    # 行选择处理
    if len(event.selection.rows) > 0:
        selected_row = event.selection.rows[0]
        selected_result = sorted_results[selected_row]
        st.session_state.selected_report_id_analysis = selected_result['result_id']
        st.session_state.view_mode_analysis = "operations"
        st.rerun()


def display_report_operations(report_id):
    """显示报告操作页面"""
    from .data_operations import load_result, delete_report  # 内部依赖导入
    # 返回按钮
    if st.button("⬅️ 返回报告列表"):
        st.session_state.view_mode_analysis = "list"
        st.rerun()
    # 加载报告
    report_data = load_result(report_id)
    if not report_data:
        st.error("❌ 无法加载报告数据")
        return
    # 头部信息
    st.markdown(f"### 📄 报告操作中心")
    col1, col2 = st.columns([3, 1])
    with col1:
        timestamp = datetime.fromisoformat(report_data['timestamp'])
        st.markdown(f"""
        **🏷️ 报告ID:** `{report_id}`  
        **🏢 集群:** {report_data['cluster_name']}  
        **⏰ 巡检时间:** {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}  
        **📋 类型:** {'⚡ 立即巡检' if report_data['inspection_type'] == 'immediate' else '⏲️ 定时巡检'}
        """)
    with col2:
        # 快速统计
        if 'inspection_results' in report_data:
            all_items = []
            for inspector_type, inspector_result in report_data['inspection_results'].items():
                items = inspector_result.get('items', [])
                all_items.extend(items)
        else:
            all_items = report_data.get('items', [])
        exception_count = 0
        passed_count = 0
        for item in all_items:
            if isinstance(item, dict):
                status = item.get('status', 'unknown')
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
            else:
                status = 'unknown'
            if status == 'passed':
                passed_count += 1
            elif status == 'exception':
                exception_count += 1
        if exception_count > 0:
            st.error(f"🔴 异常: {exception_count}")
        else:
            st.success("🟢 全部通过")
        st.info(f"📊 总计: {len(all_items)}")
    st.divider()
    # 操作按钮
    st.markdown("### 🔧 操作")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 查看详情", type="primary", use_container_width=True):
            st.session_state.view_mode_analysis = "detail"
            st.rerun()
    # 删除操作
    st.markdown("#### 🗑️ 删除操作")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("⚠️ 删除操作不可恢复，请谨慎操作")
    with col2:
        confirm_key = f"confirm_delete_{report_id}"
        if st.session_state.get(confirm_key, False):
            if st.button("❌ 确认删除", type="primary", use_container_width=True):
                try:
                    delete_report(report_id)
                    st.success(f"✅ 已删除报告: {report_id}")
                    if confirm_key in st.session_state:
                        del st.session_state[confirm_key]
                    st.session_state.view_mode_analysis = "list"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 删除失败: {str(e)}")
        else:
            if st.button("🗑️ 删除", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()
    if st.session_state.get(confirm_key, False):
        st.warning("⚠️ 点击确认删除按钮触发删除操作")


def display_report_detail(report_id):
    """显示报告详情"""
    from .data_operations import load_result  # 内部依赖导入
    # 返回按钮
    if st.button("⬅️ 返回操作页面"):
        st.session_state.view_mode_analysis = "operations"
        st.rerun()
    # 加载报告
    report_data = load_result(report_id)
    if not report_data:
        st.error("❌ 无法加载报告数据")
        return
    # 头部信息
    st.markdown(f"## 📄 巡检报告详情")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        **🏷️ 报告ID:** `{report_id}`  
        **🖥️ 集群:** {report_data['cluster_name']}  
        **⏰ 时间:** {datetime.fromisoformat(report_data['timestamp']).strftime('%Y年%m月%d日 %H:%M:%S')}  
        **📋 类型:** {'⚡ 立即巡检' if report_data['inspection_type'] == 'immediate' else '⏲️ 定时巡检'}
        """)
    with col2:
        # 快速统计
        if 'inspection_results' in report_data:
            all_items = []
            for inspector_type, inspector_result in report_data['inspection_results'].items():
                items = inspector_result.get('items', [])
                all_items.extend(items)
        else:
            all_items = report_data.get('items', [])
        exception_count = 0
        passed_count = 0
        for item in all_items:
            if isinstance(item, dict):
                status = item.get('status', 'unknown')
            elif hasattr(item, 'status'):
                status = getattr(item, 'status', 'unknown')
            else:
                status = 'unknown'
            if status == 'passed':
                passed_count += 1
            elif status == 'exception':
                exception_count += 1
        if exception_count > 0:
            st.error(f"🔴 发现 {exception_count} 个异常")
        else:
            st.success(f"🟢 所有检查通过 ({passed_count} 项)")
    st.divider()
    # 检查项详情
    display_inspection_items(all_items, report_id=report_id)


def display_inspection_items(items, report_id=None):
    """显示巡检项详情"""
    # 分类
    passed_items = [item for item in items if item.get('status') == 'passed']
    exception_critical = [item for item in items if item.get('status') == 'exception' and item.get('severity') == 'critical']
    exception_warning = [item for item in items if item.get('status') == 'exception' and item.get('severity') == 'warning']
    exception_info = [item for item in items if item.get('status') == 'exception' and item.get('severity') in ['info', 'error'] or (item.get('status') == 'exception' and item.get('severity') not in ['critical', 'warning'])]
    # 标签页
    tab_names = []
    tab_data = []
    if exception_critical:
        tab_names.append(f"🔴 严重异常 ({len(exception_critical)})")
        tab_data.append(exception_critical)
    if exception_warning:
        tab_names.append(f"🟡 一般异常 ({len(exception_warning)})")
        tab_data.append(exception_warning)
    if exception_info:
        tab_names.append(f"ℹ️ 其他异常 ({len(exception_info)})")
        tab_data.append(exception_info)
    if passed_items:
        tab_names.append(f"✅ 通过 ({len(passed_items)})")
        tab_data.append(passed_items)
    # 渲染标签页
    if tab_names:
        tabs = st.tabs(tab_names)
        for i, (tab, data) in enumerate(zip(tabs, tab_data)):
            with tab:
                display_items_list(data, tab_names[i].startswith("✅"), report_id=report_id, tab_name=tab_names[i])


def display_items_list(items, is_passed=False, report_id=None, tab_name=None):
    """显示检查项列表"""
    if not items:
        st.info("此类别下暂无项目")
        return
    for idx, item in enumerate(items):
        title = f"{item.get('name', '未知检查项')}"
        expanded = not is_passed and item.get('severity') == 'critical'
        with st.expander(title, expanded=expanded):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**描述:** {item.get('description', '无')}")
                details = item.get('details', '')
                if details:
                    if 'violations' in item and isinstance(item['violations'], list):
                        st.markdown("**违规资源:**")
                        base = f"{item.get('name','')}_{item.get('description','')[:50]}_{report_id or ''}_{tab_name or ''}_{idx}"
                        item_key = hashlib.md5(base.encode()).hexdigest()[:12]
                        safe_display_opa_violations_table(item['violations'], show_expander=False, table_key=item_key)
                    else:
                        st.markdown("**详细信息:**")
                        st.text(details)
            with col2:
                status = item.get('status', 'unknown')
                severity = item.get('severity', 'info')
                if status == 'exception':
                    if severity == 'critical':
                        st.error("🔴 严重异常")
                    elif severity == 'warning':
                        st.warning("🟡 一般异常")
                    else:
                        st.info("ℹ️ 其他异常")
                elif status == 'passed':
                    st.success("✅ 通过")
                else:
                    st.info("ℹ️ 未知状态")
            solution = item.get('solution', '')
            if solution:
                st.markdown("**💡 建议解决方案:**")
                st.info(solution)