#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告分析-AI分析模块：Tab3全逻辑、AI生成、保存修复方案
"""
import sys
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import Tuple
from pathlib import Path

# 导入OpenAI相关
from openai import OpenAI
from openai import APIError, APIConnectionError, APITimeoutError, AuthenticationError
from .path_config import RESULTS_DIR
# 导入项目模块
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from .data_operations import list_results, load_result


def normalize(v):
    """标准化值展示"""
    if v is None:
        return "无"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v)


def ai_generate(exception: dict) -> Tuple[bool, str]:
    """AI生成修复方案"""
    # 从会话状态获取AI配置
    base_url = st.session_state.get("tab3_ai_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = st.session_state.get("tab3_ai_model", "qwen-max")
    api_key = st.session_state.get("tab3_ai_api_key", "")
    timeout = st.session_state.get("tab3_ai_timeout", 60)
    
    prompt = f"""
你是资深Kubernetes集群、mysql、redis运维专家，精通K8s节点管理、监控巡检，数据库运维等工作。
请针对以下Kubernetes集群巡检以及数据节点巡检发现的异常，给出具体、可操作、分步式的修复方案：
- 节点：{exception['节点']}
- 检查项：{exception['检查项']}
- 详情：{exception['详情']}
- 结果：
{exception['结果']}
""".strip()
    # 调用AI
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a Kubernetes expert"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
    except AuthenticationError as e:
        return False, f"❌ API密钥无效/认证失败，请检查密钥是否正确（错误信息：{e}）"
    except APIConnectionError as e:
        return False, f"❌ 无法连接到AI API服务，请检查网络和API地址是否可达（错误信息：{e}）"
    except APITimeoutError as e:
        return False, f"❌ AI请求超时（已等待{timeout}秒），请增加超时时间或检查服务状态（错误信息：{e}）"
    except APIError as e:
        return False, f"❌ AI服务返回错误：{e.message}（错误码：{e.status_code}）"
    except Exception as e:
        return False, f"❌ 调用失败：{str(e)}"
    return True, resp.choices[0].message.content.strip()


def display_ai_analysis_results(report_id: str):
    """展示AI修复结果"""
    report_data = load_result(report_id)
    if not report_data:
        st.error("❌ 无法加载报告数据")
        return
    st.markdown("### 🤖 AI 修复结果")
    ai_analysis = report_data.get('ai_analysis', {})
    if ai_analysis:
        st.success("以下是已保存的AI修复结果：")
        for check_item, analysis in ai_analysis.items():
            st.markdown(f"#### 检查项: {check_item}")
            st.markdown(analysis)
            st.divider()
    else:
        st.info("暂无AI修复结果。")


def render_ai_tab():
    """渲染AI分析标签页"""
    st.markdown("利用 AI 模型生成 Kubernetes 集群巡检异常的修复方案。")
    st.markdown("### 🤖 AI 分析异常条目")
    # 1. AI配置
    with st.expander("⚙️ AI 服务配置", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "API 接口地址",
                value="https://dashscope.aliyuncs.com/compatible-mode/v1",
                key="tab3_ai_base_url"
            )
            st.text_input(
                "模型名称",
                value="qwen-max",
                key="tab3_ai_model"
            )
        with col2:
            st.text_input(
                "API KEY",
                type="password",
                key="tab3_ai_api_key"
            )
            st.number_input(
                "请求超时(秒)",
                min_value=5, max_value=180, value=60,
                key="tab3_ai_timeout"
            )
    # 2. 报告选择
    st.markdown("### 📄 选择巡检报告")
    all_results = list_results()
    if not all_results:
        st.info("暂无巡检报告")
        st.stop()
    options = [f"{r['result_id']} | {r['cluster_name']} | {r['timestamp']}" for r in all_results]
    selected = st.selectbox("选择报告", options, key="tab3_report")
    result_id = selected.split(" | ")[0]
    report_data = load_result(result_id)
    # 3. 异常提取
    st.markdown("### 🚨 异常列表")
    st.markdown('<div id="top"></div>', unsafe_allow_html=True)
    rows = []
    for group in ["node", "prometheus", "opa"]:
        items = report_data.get("inspection_results", {}).get(group, {}).get("items", [])
        for item in items:
            if item.get("status") != "passed":
                rows.append({
                    "选择": True,
                    "类型": group,
                    "节点": item.get("node", {}).get("ip", "集群级"),
                    "检查项": item.get("name"),
                    "详情": item.get("description"),
                    "结果": normalize(item.get("variables", {}).get("output") or item.get("kwargs", {}).get("metrics") or item.get("violations"))
                })
    df = pd.DataFrame(rows)
    if df.empty:
        st.success("无异常")
        st.stop()
    # 4. 异常编辑表格
    edited_df = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "选择": st.column_config.CheckboxColumn("选择"),
            "类型": st.column_config.TextColumn("类型", disabled=True),
            "节点": st.column_config.TextColumn("节点", disabled=True),
            "检查项": st.column_config.TextColumn("检查项", disabled=True),
            "详情": st.column_config.TextColumn("详情", disabled=True),
            "结果": st.column_config.TextColumn("结果", disabled=True),
        },
        key="tab3_editor"
    )
    selected_rows = edited_df[edited_df["选择"]]
    # 5. AI生成&保存
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### 📦 已保存的 AI 修复方案")
        ai_saved: dict = report_data.get("ai_analysis") or {}
        if ai_saved:
            for idx, (check_item, entry) in enumerate(ai_saved.items(), start=1):
                if not isinstance(entry, dict):
                    continue
                st.markdown(f"## 异常 {idx}：{check_item}")
                st.caption(f"模型：{entry['model']} ｜ 更新时间：{entry['updated_at']}")
                st.markdown(entry["content"])
                st.divider()
        else:
            st.info("暂无已保存方案")
        st.markdown('<a href="#top">返回顶部</a>', unsafe_allow_html=True)
    with col_right:
        # 初始化会话状态
        if "tab3_new_results" not in st.session_state:
            st.session_state["tab3_new_results"] = {}
        # 生成按钮
        title, botton = st.columns(2)
        with title:
            st.markdown("### 🤖 重新生成方案")
        with botton:
            generate_btn = st.button("立即生成", type="primary")
        # 保存成功提示
        if st.session_state.get("tab3_save_success"):
            st.success("AI 分析结果已全部保存")
            del st.session_state["tab3_save_success"]
        # 执行生成
        if generate_btn:
            if selected_rows.empty:
                st.warning("请至少选择一条异常")
            else:
                for idx, (_, row) in enumerate(selected_rows.iterrows(), start=1):
                    check_item = row["检查项"]
                    with st.spinner(f"AI 分析中{idx}/{len(selected_rows)}【请勿刷新页面！！】：{check_item}"):
                        success, new_content = ai_generate(row.to_dict())
                        st.markdown(f"## 异常：{check_item}")
                        if success:
                            st.session_state["tab3_new_results"][check_item] = new_content
                            st.markdown(new_content)
                        else:
                            st.error(new_content)
                        st.divider()
        # 保存方案
        if len(st.session_state["tab3_new_results"]) > 0 and st.button("保存全部新方案到巡检结果文件"):
            saved = False
            for file_path in RESULTS_DIR.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get("result_id") != result_id:
                        continue
                    if 'ai_analysis' not in data:
                        data['ai_analysis'] = {}
                    for check_item, content in st.session_state["tab3_new_results"].items():
                        data["ai_analysis"][check_item] = {
                            "content": content,
                            "model": st.session_state["tab3_ai_model"],
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    st.session_state.tab3_new_results = {}
                    st.session_state["tab3_save_success"] = True
                    saved = True
                    st.rerun()
                    break
                except Exception as e:
                    st.error(f"保存失败：{e}")
            if not saved:
                st.error("未找到对应的巡检结果文件")