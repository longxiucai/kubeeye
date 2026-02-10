#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告分析-数据操作模块：加载/删除/解析报告、集群列表、报告导入
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib
import streamlit as st
from datetime import datetime
import time

# 从路径配置文件统一导入路径常量
from .path_config import RESULTS_DIR

# 导入项目工具模块
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.data_cleanup import get_cleanup_manager

def list_clusters() -> List[str]:
    """列出所有集群名称"""
    return list(set(result['cluster_name'] for result in list_results()))


def list_results(cluster_name: Optional[str] = None) -> List[Dict]:
    """列出巡检结果"""
    # 定义数据目录（和原文件保持一致）
    results = []
    for file_path in RESULTS_DIR.glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            if cluster_name and result_data.get('cluster_name') != cluster_name:
                continue
            if 'summary' in result_data:
                summary_data = result_data['summary']
                passed = summary_data.get('passed', 0)
                total_exceptions = summary_data.get('error', 0) + summary_data.get('failed', 0) + summary_data.get('warning', 0)
                critical = total_exceptions
                warning = 0
                info = 0
                total = summary_data.get('total_items', 0)
            elif 'inspection_results' in result_data:
                critical = 0
                warning = 0
                info = 0
                passed = 0
                total = 0
                for inspector_type, inspector_result in result_data.get('inspection_results', {}).items():
                    items = inspector_result.get('items', [])
                    total += len(items)
                    for item in items:
                        if isinstance(item, dict):
                            status = item.get('status', 'unknown')
                        elif hasattr(item, 'status'):
                            status = getattr(item, 'status', 'unknown')
                        else:
                            status = 'unknown'
                        if status == 'passed':
                            passed += 1
                        elif status == 'exception':
                            critical += 1
                        else:
                            info += 1
            else:
                critical = 0
                warning = 0
                info = 0
                passed = 0
                for item in result_data.get('items', []):
                    if isinstance(item, dict):
                        status = item.get('status', 'unknown')
                        severity = item.get('severity', 'unknown')
                    elif hasattr(item, 'status'):
                        status = getattr(item, 'status', 'unknown')
                        severity = getattr(item, 'severity', 'unknown')
                    else:
                        status = 'unknown'
                        severity = 'unknown'
                    if status == 'passed':
                        passed += 1
                    elif severity == 'critical':
                        critical += 1
                    elif severity == 'warning':
                        warning += 1
                    else:
                        info += 1
                total = len(result_data.get('items', []))
            summary = {
                'cluster_name': result_data.get('cluster_name', ''),
                'inspection_type': result_data.get('inspection_type', 'unknown'),
                'timestamp': result_data.get('timestamp', ''),
                'result_id': result_data.get('result_id', ''),
                'total': total,
                'passed': passed,
                'critical': critical,
                'warning': warning,
                'info': info
            }
            results.append(summary)
        except Exception as e:
            continue
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    return results


def load_result(result_id: str) -> Optional[Dict]:
    """加载巡检结果"""
    for file_path in RESULTS_DIR.glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            if result_data.get('result_id') == result_id:
                return result_data
        except Exception as e:
            print(f"Warning: Failed to read {file_path}: {e}")
            continue
    possible_patterns = [
        f"inspection_result_{result_id}.json",
        f"{result_id}.json",
    ]
    if '_' in result_id:
        parts = result_id.split('_')
        if len(parts) >= 3:
            for file_path in RESULTS_DIR.glob(f'inspection_result_*_{parts[-2]}_{parts[-1]}.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    if result_data.get('result_id') == result_id:
                        return result_data
                except Exception as e:
                    print(f"Warning: Failed to read {file_path}: {e}")
                    continue
    for pattern in possible_patterns:
        result_file = RESULTS_DIR / pattern
        if result_file.exists():
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to read {result_file}: {e}")
                continue
    return None


def delete_report(report_id):
    """删除报告文件"""
    import os
    from pathlib import Path
    
    for file_path in RESULTS_DIR.glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('result_id') == report_id:
                os.remove(file_path)
                return True
        except:
            continue
    return False


def parse_inspection_metrics(report_data: dict) -> dict:
    """解析单份巡检报告的指标数据"""
    metrics_by_line = {}
    timestamp = datetime.fromisoformat(report_data['timestamp'])
    # Node 指标
    node_items = report_data.get('inspection_results', {}).get('node', {}).get('items', [])
    import re
    for item in node_items:
        rule_id = item.get('rule_id', 'unknown_rule')
        node_info = item.get('node', {})
        node_ip = node_info.get('ip', 'unknown_node_ip')
        item_name = item.get('name', '未知检查-未知节点')
        split_parts = re.split(r'\s*-\s*', item_name, maxsplit=1)
        subgraph_title = f"{rule_id}-{split_parts[0].strip()}" if split_parts else rule_id
        value_str = item.get('variables', {}).get('output', 'unknown').strip()
        item_status = item.get('status', 'unknown').strip()
        line_key = f"{rule_id}-{node_ip}"
        if line_key not in metrics_by_line:
            metrics_by_line[line_key] = {
                'metric': {
                    'type': 'node',
                    'rule_id': rule_id,
                    'subgraph_title': subgraph_title,
                    'node_ip': node_ip,
                    'item_status': item_status
                }
            }
        try:
            value = float(value_str)
            metrics_by_line[line_key][timestamp] = {
                'value_type': 'numeric',
                'value': value,
                'raw_str': value_str
            }
        except ValueError:
            metrics_by_line[line_key][timestamp] = {
                'value_type': 'categorical',
                'value': value_str,
                'status': value_str,
                'item_status': item_status
            }
    # Prometheus 指标
    prom_items = report_data.get('inspection_results', {}).get('prometheus', {}).get('items', [])
    for item in prom_items:
        prom_rule_id = item.get('rule_id', 'unknown_prom_rule')
        metrics = item.get('kwargs', {}).get('metrics', [])
        item_name = item.get('name', '')
        if not metrics:
            continue
        for metric_item in metrics:
            full_metric = metric_item.get('metric', {})
            try:
                value = float(metric_item.get('value', 0.0))
            except (ValueError, TypeError):
                value = 0.0
            prom_unique_key = hashlib.sha256(json.dumps(full_metric, sort_keys=True).encode()).hexdigest()[:8]
            line_key = f"prom_{prom_rule_id}-{prom_unique_key}"
            name_split_parts = re.split(r'\s*-\s*', item_name, maxsplit=1)
            if len(name_split_parts) > 1:
                item_name = name_split_parts[0].strip()
            subgraph_title = f"{prom_rule_id}-{item_name}"
            if line_key not in metrics_by_line:
                metrics_by_line[line_key] = {
                    'metric': {
                        'type': 'prometheus',
                        'rule_id': prom_rule_id,
                        'subgraph_title': subgraph_title,
                        'full_metric': full_metric,
                        'item_status': 'normal'
                    }
                }
            metrics_by_line[line_key][timestamp] = {
                'value_type': 'numeric',
                'value': value
            }
    # OPA 指标
    opa_items = report_data.get('inspection_results', {}).get('opa', {}).get('items', [])
    for item in opa_items:
        opa_rule_id = item.get('rule_id', 'unknown_opa_rule')
        opa_name = item.get('name', f"OPA规则-{opa_rule_id}")
        violations = item.get('violations', [])
        violations_len = len(violations)
        item_status = item.get('status', 'unknown').strip()
        subgraph_title = f"opa-{opa_rule_id}"
        line_key = f"opa_{opa_rule_id}"
        if line_key not in metrics_by_line:
            metrics_by_line[line_key] = {
                'metric': {
                    'type': 'opa',
                    'rule_id': opa_rule_id,
                    'subgraph_title': subgraph_title,
                    'violations_len': violations_len,
                    'item_status': item_status,
                    'name': opa_name
                }
            }
            metrics_by_line[line_key][timestamp] = {
                'value_type': 'numeric',
                'value': violations_len
            }
    return metrics_by_line

def handle_import(import_mode, uploaded_file, text_data):
    """处理报告导入"""
    try:
        # 读取报告内容
        if import_mode == "file":
            if not uploaded_file:
                st.error("请先上传 JSON 文件")
                return False
            report_data = json.load(uploaded_file)
        else:
            if not text_data.strip():
                st.error("请输入 JSON 内容")
                return False
            report_data = json.loads(text_data)

        # 获取 result_id 作为文件名
        result_id = report_data.get("result_id")
        if not result_id:
            st.error("报告中缺少 result_id，无法保存")
            return False
        cluster_name = report_data.get("cluster_name")
        if not cluster_name:
            st.error("报告中缺少 cluster_name，无法保存")
            return False
        filename = f"{cluster_name}_{result_id}.json"
        result_path = RESULTS_DIR / filename

        # 保存报告（存在则覆盖）
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 更新 session_state
        st.session_state.report_data = report_data

        # 尝试清理旧报告
        try:
            cleanup_manager = get_cleanup_manager()
            cleanup_manager.cleanup_inspection_results()
        except Exception as e:
            st.warning(f"清理旧报告失败: {e}")

        placeholder = st.empty()
        placeholder.success(f"报告导入成功")
        time.sleep(1.5)
        placeholder.empty()

        return True

    except json.JSONDecodeError:
        st.error("JSON 格式错误")
        return False
    except Exception as e:
        st.error(f"导入失败：{e}")
        return False
