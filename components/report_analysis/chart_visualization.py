#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告分析-图表可视化模块：Node/Prom/OPA指标绘图、可视化常量
"""
import json
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import matplotlib.pyplot as plt
from itertools import cycle
from pathlib import Path
from datetime import datetime

# 导入项目工具模块
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ================= 全局常量（原文件直接复制，无修改） =================
# 非数值型指标-状态颜色映射
STATUS_COLOR_MAP = {
    'passed': '#2ECC71',
    'exception': '#E74C3C',
    'failed': '#F39C12',
    'unknown': '#F39C12',
    'error': '#E74C3C',
    'warning': '#F39C12',
    'skipped': '#95A5A6',
    'not_applicable': '#95A5A6',
    'invalid': '#95A5A6',
    'not_executed': '#95A5A6'
}
DEFAULT_STATUS_COLOR = '#95A5A6'

# 全局颜色配置
COLOR_POOL = plt.cm.tab20.colors + plt.cm.Set3.colors
color_cycle = cycle(COLOR_POOL)
COLOR_MAP = {}  # line_key -> color


def mpl_color_to_plotly(color):
    """matplotlib颜色转plotly"""
    if len(color) == 3:
        r, g, b = color
        return f"rgb({int(r*255)},{int(g*255)},{int(b*255)})"
    elif len(color) == 4:
        r, g, b, a = color
        return f"rgba({int(r*255)},{int(g*255)},{int(b*255)},{a})"
    else:
        raise ValueError(f"Unsupported color format: {color}")

def get_color_by_line_key(line_key: str) -> str:
    """为同一节点分配固定颜色"""
    if line_key not in COLOR_MAP:
        COLOR_MAP[line_key] = next(color_cycle)
    return mpl_color_to_plotly(COLOR_MAP[line_key])


def display_node_metrics(node_df: pd.DataFrame, selected_cluster: str):
    """展示Node指标"""
    all_rules = sorted(node_df['rule_id'].unique())

    multiselect_key = "node_rule_select"

    # 初始化默认值（避免每次rerun覆盖用户选择）
    if multiselect_key not in st.session_state:
        st.session_state[multiselect_key] = []

    multiselect_, select_btn = st.columns([0.95, 0.05])

    with select_btn:
        st.markdown("<div style='height: 27px'></div>", unsafe_allow_html=True)
        if st.button("全选", key="node_all_btn", type="secondary"):
            st.session_state[multiselect_key] = all_rules.copy()
    with multiselect_:
        selected_rules = st.multiselect(
            label=f"选择要展示的 Node 指标（不选则不显示）共 {len(all_rules)} 个指标",
            options=all_rules,
            key=multiselect_key
        )

    if not selected_rules:
        st.info("请选择要查看的 Node 指标")
        return

    node_df_selected = node_df[node_df['rule_id'].isin(selected_rules)]

    node_numeric_df = node_df_selected[node_df_selected['value_type'] == 'numeric']
    node_categorical_df = node_df_selected[node_df_selected['value_type'] == 'categorical']
    node_numeric_groups = sorted(node_numeric_df['rule_id'].unique())
    node_categorical_groups = sorted(node_categorical_df['rule_id'].unique())
    total_rows = len(node_numeric_groups) + len(node_categorical_groups)
    if total_rows == 0:
        return
    # 子图标题
    subplot_titles = []
    for rule in node_numeric_groups:
        subplot_titles.append(node_numeric_df[node_numeric_df['rule_id'] == rule]['subgraph_title'].iloc[0])
    for rule in node_categorical_groups:
        title = node_categorical_df[node_categorical_df['rule_id'] == rule]['subgraph_title'].iloc[0]
        subplot_titles.append(f"{title}（非数值）")
    # 创建子图
    vertical_spacing = min(0.06, 0.9 / max(total_rows - 1, 1))
    fig = make_subplots(
        rows=total_rows,
        cols=1,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=vertical_spacing,
        figure=go.Figure(layout=go.Layout(height=320 * total_rows))
    )
    shown_legends = set()
    current_row = 1
    # 数值型指标
    for rule in node_numeric_groups:
        group_df = node_numeric_df[node_numeric_df['rule_id'] == rule]
        for ip in sorted(group_df['node_ip'].unique()):
            ip_df = group_df[group_df['node_ip'] == ip]
            if ip_df.empty:
                continue
            show_legend = ip not in shown_legends
            node_color = get_color_by_line_key(ip)
            fig.add_trace(
                go.Scatter(
                    x=ip_df['time'],
                    y=ip_df['numeric_val'],
                    name=f"节点 {ip}",
                    legendgroup=f"entity_{ip}",
                    showlegend=show_legend,
                    mode='lines+markers',
                    line=dict(width=1.5, color=node_color),
                    marker=dict(size=4, color=node_color),
                    hovertemplate=f"<br>节点: {ip}<br>时间: %{{x}}<br>数值: %{{y}}<extra></extra>"
                ),
                row=current_row, col=1
            )
            if show_legend:
                shown_legends.add(ip)
        current_row += 1
    # 非数值型指标
    for rule in node_categorical_groups:
        group_df = node_categorical_df[node_categorical_df['rule_id'] == rule]
        for ip in sorted(group_df['node_ip'].unique()):
            ip_df = group_df[group_df['node_ip'] == ip].sort_values('time')
            if ip_df.empty:
                continue
            status_colors = [STATUS_COLOR_MAP.get(s, DEFAULT_STATUS_COLOR) for s in ip_df['show_status']]
            show_legend = ip not in shown_legends
            node_color = get_color_by_line_key(ip)
            # 虚线
            fig.add_trace(
                go.Scatter(
                    x=ip_df['time'],
                    y=[1]*len(ip_df),
                    mode='lines',
                    line=dict(width=0.2, color=node_color, dash='dot'),
                    hoverinfo='none',
                    legendgroup=f"entity_{ip}",
                    showlegend=False
                ),
                row=current_row, col=1
            )
            # 标记点
            fig.add_trace(
                go.Scatter(
                    x=ip_df['time'],
                    y=[1]*len(ip_df),
                    mode='markers',
                    name=f"节点 {ip}",
                    legendgroup=f"entity_{ip}",
                    showlegend=show_legend,
                    marker=dict(
                        size=8,
                        color=status_colors,
                        line=dict(width=1.5, color='white')
                    ),
                    customdata=ip_df[['show_status', 'categorical_val']].assign(node_ip=ip).values,
                    hovertemplate=f"<br>节点: {ip}<br>时间: %{{x}}<br>状态: %{{customdata[0]}}<br>值: %{{customdata[1]}}<extra></extra>"
                ),
                row=current_row, col=1
            )
            if show_legend:
                shown_legends.add(ip)
        fig.update_yaxes(visible=False, row=current_row, col=1)
        current_row += 1
    # 图表样式
    fig.update_layout(
        title=f"{selected_cluster} - Node 指标",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(
            itemclick="toggleothers",
            itemdoubleclick="toggle",
            orientation="h",
            yanchor="bottom",
            y=-0.04,
            xanchor="center",
            x=0.5
        )
    )
    fig.update_xaxes(showline=True, mirror=True)
    fig.update_yaxes(showline=True, mirror=True)
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})


def display_prom_metrics(prom_df: pd.DataFrame, selected_cluster: str):
    """展示Prometheus指标"""
    if prom_df.empty:
        st.info("📊 无 Prometheus 可视化指标")
        return
    PROM_RULE_LINE_THRESHOLD = 30
    prom_groups = sorted(prom_df['rule_id'].unique())
    inline_rules = []
    standalone_rules = []
    # 分类规则
    for rule in prom_groups:
        line_cnt = prom_df[prom_df['rule_id'] == rule]['line_key'].nunique()
        if line_cnt > PROM_RULE_LINE_THRESHOLD:
            standalone_rules.append(rule)
        else:
            inline_rules.append(rule)
    # 子图版Prom指标
    if inline_rules:
        subplot_titles = [f"{prom_df[prom_df['rule_id'] == rule]['subgraph_title'].iloc[0]}" for rule in inline_rules]
        total_rows = len(inline_rules)
        vertical_spacing = min(0.02, 0.9 / max(total_rows - 1, 1))
        fig = make_subplots(
            rows=total_rows,
            cols=1,
            subplot_titles=subplot_titles,
            shared_xaxes=True,
            vertical_spacing=vertical_spacing,
            figure=go.Figure(layout=go.Layout(height=320 * total_rows))
        )
        shown_legends = set()
        current_row = 1
        for rule in inline_rules:
            group_df = prom_df[prom_df['rule_id'] == rule]
            for line_key in sorted(group_df['line_key'].unique()):
                line_df = group_df[group_df['line_key'] == line_key]
                if line_df.empty:
                    continue
                metric_info = line_df['metric_info'].iloc[0]
                metric = metric_info.get('full_metric', {})
                metric_str = json.dumps(metric, sort_keys=True, ensure_ascii=False)
                color = get_color_by_line_key(line_key)
                show_legend = line_key not in shown_legends
                if show_legend:
                    shown_legends.add(line_key)
                fig.add_trace(
                    go.Scatter(
                        x=line_df['time'],
                        y=line_df['numeric_val'],
                        legendgroup=f"entity_{line_key}",
                        showlegend=show_legend,
                        mode='lines+markers',
                        line=dict(width=1.5, color=color),
                        marker=dict(size=4),
                        hovertemplate=(
                            "%{y}<br>"
                            f"Metric: {metric_str}"
                            "<extra></extra>"
                        )
                    ),
                    row=current_row, col=1
                )
            current_row += 1
        # 样式
        fig.update_layout(
            title=f"{selected_cluster} 集群 - Prometheus 指标",
            hovermode='x unified',
            template='plotly_white',
            margin=dict(t=60, b=60),
            showlegend=False
        )
        fig.update_xaxes(showline=True, mirror=True)
        fig.update_yaxes(showline=True, mirror=True)
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})
    # 独立版Prom指标
    for rule in standalone_rules:
        group_df = prom_df[prom_df['rule_id'] == rule]
        title = group_df['subgraph_title'].iloc[0]
        st.markdown(f"### 📈 Prometheus - {title}")
        # 构造可选项
        line_key_to_metric = {}
        for line_key in sorted(group_df['line_key'].unique()):
            metric_info = group_df[group_df['line_key'] == line_key]['metric_info'].iloc[0]
            metric = metric_info.get('full_metric', {})
            metric_str = json.dumps(metric, sort_keys=True, ensure_ascii=False)
            line_key_to_metric[line_key] = metric_str
        metric_to_line_keys = {}
        for line_key, metric_str in line_key_to_metric.items():
            metric_to_line_keys.setdefault(metric_str, set()).add(line_key)
        metric_options = list(metric_to_line_keys.keys())

        rule_id = group_df['rule_id'].iloc[0]
        multiselect_key = f"prom_filter_{rule_id}"
        if multiselect_key not in st.session_state:
            st.session_state[multiselect_key] = metric_options[:5]
        # 全选按钮+多选框
        multiselect_, select_btn = st.columns([0.95, 0.05])
        with select_btn:
            st.markdown("<div style='height: 27px'></div>", unsafe_allow_html=True)
            if st.button("全选", key=f"prom_all_btn_{rule}", type="secondary"):
                st.session_state[multiselect_key] = metric_options.copy()
        with multiselect_:
            selected_options = st.multiselect(
                label=f"选择要展示的指标（不选则不显示）共 {len(metric_options)} 可选指标",
                options=metric_options,
                key=multiselect_key
            )
        # 筛选线条
        selected_line_keys = set()
        for metric_str in selected_options:
            selected_line_keys |= metric_to_line_keys.get(metric_str, set())
        # 绘图
        fig = go.Figure()
        for line_key in sorted(group_df['line_key'].unique()):
            if line_key not in selected_line_keys:
                continue
            line_df = group_df[group_df['line_key'] == line_key]
            if line_df.empty:
                continue
            metric_str = line_key_to_metric[line_key]
            color = get_color_by_line_key(line_key)
            fig.add_trace(
                go.Scatter(
                    x=line_df['time'],
                    y=line_df['numeric_val'],
                    mode='lines+markers',
                    line=dict(width=1, color=color),
                    marker=dict(size=4),
                    hovertemplate=(
                        "%{y}<br>"
                        f"Metric: {metric_str}"
                        "<extra></extra>"
                    ),
                    showlegend=False
                )
            )
        # 样式
        fig.update_layout(
            title=f"{selected_cluster} 集群 - Prometheus 指标 - {title}",
            hovermode='x unified',
            template='plotly_white',
            margin=dict(t=60, b=60)
        )
        fig.update_xaxes(showline=True, mirror=True)
        fig.update_yaxes(showline=True, mirror=True)
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})


def display_opa_metrics(opa_df: pd.DataFrame, selected_cluster: str):
    """展示OPA指标"""
    if opa_df.empty:
        st.info("📊 无 OPA 可视化指标")
        return
    opa_df['rule_name'] = opa_df['metric_info'].apply(lambda x: x.get('name', 'unknown_opa_rule'))
    opa_df['line_key'] = opa_df['rule_id']
    fig = go.Figure()
    shown_legends = set()
    # 绘图
    for line_key in sorted(opa_df['line_key'].unique()):
        line_df = opa_df[opa_df['line_key'] == line_key].sort_values('time')
        if line_df.empty:
            continue
        rule_name = line_df['rule_name'].iloc[0]
        color = get_color_by_line_key(line_key)
        show_legend = line_key not in shown_legends
        fig.add_trace(
            go.Scatter(
                x=line_df['time'],
                y=line_df['numeric_val'],
                mode='lines+markers',
                name=rule_name,
                showlegend=show_legend,
                line=dict(width=1.5, color=color),
                marker=dict(size=6, color=color, symbol='circle'),
                hovertemplate=f"{rule_name}<br>违规数量: %{{y}}<br>时间: %{{x}}<extra></extra>"
            )
        )
        if show_legend:
            shown_legends.add(line_key)
    # 样式
    fig.update_layout(
        title=f"{selected_cluster} 集群 - OPA 规则违规数量",
        template="plotly_white",
        hovermode="x unified",
        yaxis_title="违规数量",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            itemclick="toggleothers",
            itemdoubleclick="toggle",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(size=10)
        ),
    )
    fig.update_xaxes(showline=True, mirror=True)
    fig.update_yaxes(showline=True, mirror=True)
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})


def display_reports_analysis(filtered_results):
    """报告分析核心函数"""
    from .data_operations import load_result, parse_inspection_metrics  # 内部依赖导入
    st.markdown("### 📊 报告分析")
    if not filtered_results:
        st.info("📭 暂无符合条件的报告")
        return
    # 单集群校验
    cluster_names = list(set(r['cluster_name'] for r in filtered_results))
    if len(cluster_names) > 1:
        st.warning("🔧 请先选择单个集群进行分析")
        return
    selected_cluster = cluster_names[0]
    # 加载详细报告
    detailed_reports = [load_result(r['result_id']) for r in filtered_results if load_result(r['result_id'])]
    if not detailed_reports:
        st.info("📭 暂无详细报告数据")
        return
    # 解析所有指标
    all_metrics = {}
    for report in detailed_reports:
        parsed = parse_inspection_metrics(report)
        for k, v in parsed.items():
            if k not in all_metrics:
                all_metrics[k] = v.copy()
            else:
                for kk, vv in v.items():
                    if kk != 'metric':
                        all_metrics[k][kk] = vv
    # 构建DataFrame
    rows = []
    for line_key, metric_data in all_metrics.items():
        metric_info = metric_data.get('metric', {})
        timestamps = {k: v for k, v in metric_data.items() if isinstance(k, datetime)}
        if not timestamps:
            continue
        subgraph_title = metric_info.get('subgraph_title', metric_info.get('rule_id', '未知子图'))
        for ts, val in timestamps.items():
            row = {
                'time': ts,
                'line_key': line_key,
                'metric_info': metric_info,
                'rule_id': metric_info.get('rule_id', ''),
                'subgraph_title': subgraph_title,
                'node_ip': metric_info.get('node_ip', ''),
                'metric_type': metric_info.get('type', ''),
                'item_status': metric_info.get('item_status', 'unknown'),
                'value_type': 'numeric',
                'numeric_val': None,
                'categorical_val': None,
                'show_status': None
            }
            if isinstance(val, dict):
                row['value_type'] = val.get('value_type')
                if row['value_type'] == 'numeric':
                    row['numeric_val'] = val.get('value')
                else:
                    row['categorical_val'] = val.get('value')
                    row['show_status'] = val.get('item_status')
            else:
                row['numeric_val'] = val
            rows.append(row)
    if not rows:
        st.info("📊 无可分析指标")
        return
    # 处理DataFrame
    df = pd.DataFrame(rows).sort_values('time')
    df['metric_type'] = df['metric_info'].apply(lambda x: x.get('type'))
    # 拆分指标
    node_df = df[df['metric_type'] == 'node']
    prom_df = df[df['metric_type'] == 'prometheus']
    opa_df = df[df['metric_type'] == 'opa'].copy()
    # 可视化
    if not node_df.empty:
        display_node_metrics(node_df, selected_cluster)
    if not prom_df.empty:
        display_prom_metrics(prom_df, selected_cluster)
    if not opa_df.empty:
        display_opa_metrics(opa_df, selected_cluster)