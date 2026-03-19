#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化规则管理组件 - 支持GitOps模式
"""
import time
import streamlit as st
import yaml
import json
import git
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from utils.rule_loader import load_rules, save_rule, Rule, RULES_DIR
from utils.cluster_config import list_clusters, get_cluster
from components.ui.inspection_engine import execute_inspection_unified

def _rules_signature(rule_type: Optional[str] = None) -> Tuple[Tuple[str, int, int], ...]:
    """
    生成规则文件签名，用于缓存失效：
    - 规则 YAML 文件新增/删除/修改（mtime/size变化）会导致签名变化
    - 支持 rule_type=None，此时遍历所有规则类型（node/prometheus/opa）
    """
    root_dir = Path(__file__).resolve().parents[1]
    rules_root = root_dir / "rules"
    sig: List[Tuple[str, int, int]] = []

    # 处理 rule_type=None 的情况：遍历所有规则类型
    if rule_type is None:
        rule_types = ["node", "prometheus", "opa"]
        for rt in rule_types:
            rules_dir = rules_root / rt
            if rules_dir.exists():
                for p in sorted(rules_dir.glob("*.yaml")):
                    try:
                        stat = p.stat()
                        sig.append((str(p), int(stat.st_mtime_ns), int(stat.st_size)))
                    except OSError:
                        continue
    # 处理指定 rule_type 的情况
    else:
        rules_dir = rules_root / rule_type
        if rules_dir.exists():
            for p in sorted(rules_dir.glob("*.yaml")):
                try:
                    stat = p.stat()
                    sig.append((str(p), int(stat.st_mtime_ns), int(stat.st_size)))
                except OSError:
                    continue

    return tuple(sig)

@st.cache_resource(show_spinner=False)
def cached_load_rules(rule_type: Optional[str] = None, include_disabled: bool = False, signature: Tuple[Tuple[str, int, int], ...] = None) -> List[Rule]:
    """
    缓存已启用规则的解析结果。signature 参与缓存 key，文件变化自动失效。
    """
    return load_rules(rule_type, include_disabled)

@st.cache_resource(show_spinner=False)
def cached_load_rules_sorted(
    rule_type: Optional[str] = None, 
    include_disabled: bool = False, 
    signature: Tuple[Tuple[str, int, int], ...] = None
) -> List[Rule]:
    """
    缓存按ID小写排序后的规则列表（复用原始缓存，性能最优）
    """
    raw_rules = cached_load_rules(rule_type, include_disabled, signature)
    return sorted(raw_rules, key=lambda x: x.id.lower())

# GitOps配置
GITOPS_CONFIG_FILE = Path(__file__).parent.parent / "data" / "gitops_config.json"
DEFAULT_RULE_REPOS = [
    {
        "name": "KubeEye官方规则库",
        "url": "https://github.com/kubesphere/kubeeye",
        "branch": "rules",
        "description": "KubeEye官方维护的规则库，包含经过验证的Kubernetes检查规则和最佳实践"
    }
]

class GitOpsRuleManager:
    """GitOps规则管理器"""
    
    def __init__(self):
        self.config_file = GITOPS_CONFIG_FILE
        self.local_rules_dir = RULES_DIR
        self.git_rules_dir = Path(__file__).parent.parent / "data" / "git_rules"
        self.git_rules_dir.mkdir(parents=True, exist_ok=True)
        
    def load_config(self) -> Dict:
        """加载GitOps配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "mode": "local",  # local 或 gitops
            "current_repository": None,  # 当前启用的单个仓库
            "auto_sync": False,
            "sync_interval": 3600  # 秒
        }
    
    def save_config(self, config: Dict):
        """保存GitOps配置"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def clone_or_update_repo(self, repo_url: str, repo_name: str, branch: str = "main") -> Tuple[bool, str]:
        """克隆或更新Git仓库"""
        repo_path = self.git_rules_dir / repo_name
        
        try:
            if repo_path.exists():
                # 更新现有仓库
                repo = git.Repo(repo_path)
                origin = repo.remotes.origin
                origin.pull(branch)
                message = f"仓库 {repo_name} 更新成功"
            else:
                # 克隆新仓库
                git.Repo.clone_from(repo_url, repo_path, branch=branch)
                message = f"仓库 {repo_name} 克隆成功"
            
            return True, message
        except Exception as e:
            return False, f"操作失败: {str(e)}"
    
    def get_repo_rules(self, repo_name: str) -> List[Rule]:
        """获取Git仓库中的规则"""
        repo_path = self.git_rules_dir / repo_name
        rules = []
        
        if not repo_path.exists():
            return rules
        
        # 遍历仓库中的规则文件
        for rule_type in ["node", "prometheus", "opa"]:
            type_dir = repo_path / rule_type
            if type_dir.exists():
                for yaml_file in type_dir.glob("*.yaml"):
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            rule_data = yaml.safe_load(f)
                        
                        if isinstance(rule_data, dict):
                            # 标记为Git规则
                            rule_data['source'] = 'git'
                            rule_data['repository'] = repo_name
                            rule_data['file_path'] = str(yaml_file.relative_to(repo_path))
                            rules.append(Rule(rule_data))
                    except Exception as e:
                        st.warning(f"加载规则文件 {yaml_file} 失败: {e}")
        
        return rules
    
    def sync_git_rule_to_local(self, rule: Rule, target_type: str) -> bool:
        """将Git规则同步到本地"""
        try:
            # 创建本地规则文件
            local_file = self.local_rules_dir / target_type / f"{rule.id}.yaml"
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 移除Git特有字段
            rule_data = rule.to_dict()
            rule_data.pop('source', None)
            rule_data.pop('repository', None) 
            rule_data.pop('file_path', None)
            
            with open(local_file, 'w', encoding='utf-8') as f:
                yaml.dump(rule_data, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            st.error(f"同步规则失败: {e}")
            return False
        
RULE_SCOPE_CONFIGS: Dict[str, Dict] = {
    "node": {
        "allowed_scope_keys": ["node_selector"],
        "required_scope_key": "node_selector",
        "scope_sub_keys": {"node_selector": []}
    },
    "opa": {
        "allowed_scope_keys": ["namespaces"],
        "required_scope_key": "namespaces",
        "scope_sub_keys": {"namespaces": ["include", "exclude"]}
    },
    "prometheus": {
        "allowed_scope_keys": [],
        "required_scope_key": "",
        "scope_sub_keys": {}
    }
}
def validate_scope_format(rule_type: str, scope_config: dict) -> Tuple[bool, List[str]]:
    """
    校验不同规则类型的scope格式是否合法（修复空值/格式错误问题 + 复用配置 + 实际使用sub_keys）
    :param rule_type: 规则类型 (node/opa/prometheus)
    :param scope_config: scope配置字典
    :return: (是否合法, 错误信息列表)
    """
    errors = []

    # 如果scope为空，直接返回合法（非必填）
    if not scope_config or scope_config == {}:
        return True, errors
    
    # 通用校验：scope必须是字典类型
    if not isinstance(scope_config, dict):
        errors.append(f"{rule_type}规则的scope必须是字典格式")
        return False, errors
    
    # 获取当前规则类型的scope配置（复用常量）
    scope_cfg = RULE_SCOPE_CONFIGS.get(rule_type, {})
    allowed_keys = scope_cfg.get("allowed_scope_keys", [])
    required_key = scope_cfg.get("required_scope_key", "")
    sub_keys = scope_cfg.get("scope_sub_keys", {})  # 现在会实际使用这个变量

    # 如果当前规则类型不支持scope，直接报错
    if rule_type != "prometheus" and not allowed_keys:
        errors.append(f"{rule_type}规则不支持配置scope，请留空")
        return False, errors

    # 1. 检查必填键是否存在（仅当有必填键时）
    if required_key and required_key not in scope_config:
        errors.append(f"{rule_type}规则的scope中必须包含{required_key}键（即使值为空）")
    else:
        # 2. 检查非法键（仅允许配置中声明的键）
        invalid_keys = [k for k in scope_config.keys() if k not in allowed_keys]
        if invalid_keys:
            errors.append(f"{rule_type}规则的scope中包含非法键: {', '.join(invalid_keys)}，仅支持{', '.join(allowed_keys)}")
        
        # 3. 针对每个合法键做格式校验
        for key in allowed_keys:
            if key not in scope_config:
                continue  # 前面已经检查必填键，这里跳过非必填的情况
            
            value = scope_config[key]
            # 获取当前键对应的必填子键列表
            required_sub_keys = sub_keys.get(key, [])
            
            # Node规则：node_selector必须是非空字典且键值对为非空字符串
            if rule_type == "node" and key == "node_selector":
                # 检查是否为字典
                if not isinstance(value, dict):
                    errors.append(f"Node规则的scope中，{key}必须是键值对格式（如: kubernetes.io/os: linux）")
                else:
                    # 检查是否为空字典（空字典不合法）
                    if not value:
                        errors.append(f"Node规则的scope中，{key}不能为空字典，请填写具体的节点标签键值对")
                    else:
                        # 检查每个键值对是否为非空字符串
                        for k, v in value.items():
                            if not isinstance(k, str) or not k.strip():
                                errors.append(f"Node规则scope的{key}中，键 '{k}' 不能为空字符串")
                            if not isinstance(v, str) or not v.strip():
                                errors.append(f"Node规则scope的{key}中，值 '{v}' (对应键 '{k}') 不能为空字符串")
            
            # OPA规则：namespaces校验（核心：使用sub_keys变量）
            elif rule_type == "opa" and key == "namespaces":
                if not isinstance(value, dict):
                    errors.append(f"OPA规则的scope中，{key}必须是字典格式（包含include/exclude字段）")
                else:
                    # 🌟 实际使用sub_keys：检查是否包含必填的子键
                    missing_sub_keys = [sk for sk in required_sub_keys if sk not in value]
                    if missing_sub_keys:
                        errors.append(f"OPA规则scope的{key}中缺少必填子键: {', '.join(missing_sub_keys)}")
                    
                    # 遍历所有子键（从配置中读取，而非硬编码）
                    for sub_key in required_sub_keys:
                        sub_value = value.get(sub_key, [])
                        # 检查子键值的类型
                        if not isinstance(sub_value, list):
                            errors.append(f"OPA规则scope的{key}.{sub_key}必须是字符串列表")
                        else:
                            # 检查列表中的元素是否为非空字符串
                            for ns in sub_value:
                                if not isinstance(ns, str) or not ns.strip():
                                    errors.append(f"OPA规则scope的{key}.{sub_key}中，值 '{ns}' 不能为空字符串")
                    
                    # 至少一个子字段不能为空（避免空配置）
                    include = value.get("include", [])
                    exclude = value.get("exclude", [])
                    if not include and not exclude:
                        errors.append(f"OPA规则的scope中，{key}不能是空配置，至少填写include或exclude其中一个")

    return len(errors) == 0, errors

def validate_rule_config(rule_type: str, rule_name: str, rule_desc: str, rule_config: dict) -> Tuple[bool, List[str]]:
    """
    通用规则配置校验函数（整合所有校验逻辑）
    :param rule_type: 规则类型 (node/prometheus/opa)
    :param rule_name: 规则名称
    :param rule_desc: 规则描述
    :param rule_config: 规则配置字典（含scope）
    :return: (是否合法, 错误信息列表)
    """
    errors = []
    
    # 1. 基础必填项校验
    if not rule_name.strip():
        errors.append("规则名称不能为空")
    if not rule_desc.strip():
        errors.append("规则描述不能为空")
    
    # 2. 配置核心项校验
    if rule_type == 'node':
        exec_content = rule_config.get('execution', {})
        assert_content = rule_config.get('assertions', {})
        if not exec_content or not assert_content:
            errors.append("节点规则必须填写执行配置与断言配置")
    
    elif rule_type == 'prometheus':
        query_content = rule_config.get('query', '').strip()
        assert_content = rule_config.get('assertions', {})
        if not query_content or not assert_content:
            errors.append("Prometheus规则必须填写查询语句与断言配置")
    
    elif rule_type == 'opa':
        rego_content = rule_config.get('rego', {})
        assert_content = rule_config.get('assertions', {})
        # 核心修改：仅校验inline字段，完全忽略file（编辑器已移除file功能）
        is_rego_valid = False
        if isinstance(rego_content, dict):
            # 只检查inline是否非空，不再考虑file
            inline = rego_content.get('inline', '').strip()
            is_rego_valid = len(inline) > 0
        # 断言配置仍需非空
        if not is_rego_valid or not assert_content:
            errors.append("OPA规则必须填写Rego内联代码与断言配置")  # 提示文案也优化，更精准
    
    # 3. Scope格式校验
    scope_config = rule_config.get('scope', {})
    is_scope_valid, scope_errors = validate_scope_format(rule_type, scope_config)
    if not is_scope_valid:
        errors.extend(scope_errors)
    return len(errors) == 0, errors

def show_validation_errors(error_messages: List[str], prefix: str = "❌"):
    """
    统一显示校验错误信息
    :param error_messages: 错误信息列表
    :param prefix: 提示前缀
    """
    st.error(f"{prefix} 操作失败，必填项未填写或格式错误：")
    for msg in error_messages:
        st.error(f"  - {msg}")

# ===== 核心功能：规则测试辅助函数 =====
def delete_test_result_file(message: str):
    """通用函数：从测试结果消息中解析并删除测试结果文件"""
    try:
        result_path = None
        if isinstance(message, str) and "已保存到:" in message:
            result_path = message.split("已保存到:", 1)[-1].strip()
        if result_path:
            result_path = Path(result_path).resolve()
            try:
                p = Path(result_path)
                if p.exists():
                    p.unlink()
                    import logging
                    logging.getLogger(__name__).info(f"成功删除临时巡检结果文件: {result_path}")
            except Exception as e:
                st.error(f"删除测试结果文件时发生错误: {e}")
    except Exception as e:
        st.error(f"解析或删除文件时发生异常: {str(e)}")

def run_rule_test(rule_id: str, rule_type: str, selected_cluster: str, tmp_id: Optional[str] = None, temp_config: Optional[Dict] = None):
    """
    执行规则测试（修复：支持传入临时配置，无需先保存）
    :param temp_config: 实时编辑的配置（未保存）
    """
    target_rule_id = tmp_id if tmp_id else rule_id
    selected_rules = {rule_type: [target_rule_id]}
    
    cluster_cfg = get_cluster(selected_cluster)
    if not cluster_cfg:
        st.error(f"无法获取集群配置: {selected_cluster}")
        return
    
    nodes = cluster_cfg.get_nodes() if hasattr(cluster_cfg, 'get_nodes') else []
    prom_cfg = cluster_cfg.get_prometheus_config() if hasattr(cluster_cfg, 'get_prometheus_config') else {}
    kubeconfig = cluster_cfg.get_kubeconfig() if hasattr(cluster_cfg, 'get_kubeconfig') else ""

    can_run = True
    if rule_type == 'node' and not nodes:
        st.error("当前集群未配置节点信息，无法执行节点规则测试")
        can_run = False
    if rule_type == 'prometheus' and not (prom_cfg and prom_cfg.get('enabled', False)):
        st.error("当前集群未配置或未启用 Prometheus，无法执行 Prometheus 规则测试")
        can_run = False
    if rule_type == 'opa' and not kubeconfig:
        st.error("当前集群未配置 kubeconfig，无法执行 OPA 规则测试")
        can_run = False

    try:
        if temp_config and tmp_id:
            # 创建临时规则文件
            temp_rule_path = RULES_DIR / rule_type / f"{tmp_id}.yaml"
            temp_rule_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 构造完整的规则数据
            temp_rule_data = {
                'id': tmp_id,
                'type': rule_type,
                'name': f"tmp_test_{tmp_id}",
                'enabled': True,
                'config': temp_config,
                'severity': 'info',
                'category': 'test'
            }
            
            # 写入临时文件
            with open(temp_rule_path, 'w', encoding='utf-8') as f:
                yaml.dump(temp_rule_data, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        st.error(f"创建临时测试规则失败: {e}")
        can_run = False

    if can_run:
        with st.spinner("正在测试规则..."):
            try:
                # 执行测试
                success, message, results = execute_inspection_unified(
                    cluster_name=selected_cluster,
                    selected_rules=selected_rules,
                    inspection_type="test",
                    show_progress=True,
                    show_ui_feedback=False
                )

                if not success:
                    st.error(f"❌ 测试执行失败: {message}")
                else:
                    st.success(f"✅ 测试执行完成")
                    inspector_result = None
                    if isinstance(results, dict):
                        inspector_result = results.get(rule_type)
                    else:
                        inspector_result = results

                    try:
                        if inspector_result is None:
                            st.warning("未生成指定类型的巡检结果（可能被跳过）")
                        else:
                            if hasattr(inspector_result, 'get_summary'):
                                summary = inspector_result.get_summary()
                                st.markdown("**测试摘要**")
                                st.json(summary)
                                st.markdown("**检查项详情**")
                                items = inspector_result.get_items() if hasattr(inspector_result, 'get_items') else getattr(inspector_result, 'items', None)
                                if items:
                                    st.write(f"共 {len(items)} 条检查项：")
                                    st.json(items)
                                else:
                                    st.info("没有检查到具体项")
                            else:
                                st.json(inspector_result)
                    except Exception as e:
                        st.error(f"展示结果失败: {e}")

                delete_test_result_file(message)
            except Exception as e:
                st.error(f"执行规则测试时发生异常: {str(e)}")
        
        if tmp_id:
            try:
                tmp_fp = RULES_DIR / rule_type / f"{tmp_id}.yaml"
                if tmp_fp.exists():
                    tmp_fp.unlink()
            except Exception as e:
                st.warning(f"清理临时文件失败: {e}")
def render_rule_editor(rule: Rule, key_suffix: str = "") -> dict:
    """
    渲染规则编辑器（创建/编辑通用，实时读取输入框值）
    返回：输入框实时解析后的完整配置（含scope）
    """
    base_key = f"rule_editor_{rule.type}_{key_suffix}"  # 简化key，保证唯一性
    cfg = {}  # 全新初始化，不依赖rule.config的旧值，纯实时读取
    st.markdown("##### 可编辑的配置")
    # ===== 节点规则 =====
    if rule.type == 'node':
        # 执行配置
        exec_raw = st.text_area(
            "执行配置 (YAML)", 
            value=yaml.dump(rule.config.get('execution', {}), allow_unicode=True).rstrip('\n'), 
            key=f"{base_key}_execution",
            height=80
        )
        try:
            cfg['execution'] = yaml.safe_load(exec_raw) if exec_raw.strip() else {}
        except Exception as e:
            st.warning(f"执行配置解析失败，将使用空配置: {e}")
            cfg['execution'] = {}
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_exec_content = """
                command: free | awk 'NR==2{printf "%.0f", $3*100/$2 }'
                timeout: 5
            """
            st.code(yaml_exec_content, language="yaml", line_numbers=False)
        # 断言配置
        assertions_raw = st.text_area(
            "断言配置 (YAML)", 
            value=yaml.dump(rule.config.get('assertions', {}), allow_unicode=True).rstrip('\n'), 
            key=f"{base_key}_assertions",
            height=128
        )
        try:
            cfg['assertions'] = yaml.safe_load(assertions_raw) if assertions_raw.strip() else {}
        except Exception as e:
            st.warning(f"断言配置解析失败，将使用空配置: {e}")
            cfg['assertions'] = {}
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_assertions_content = """
                - condition: int(output) < 80
                  description: '内存使用率: {{ output }}%'
                  name: 内存使用率正常
                  severity: warning
            """
            st.code(yaml_assertions_content, language="yaml", line_numbers=False)
        # Scope作用域（核心：实时读取）
        scope_raw = st.text_area(
            "作用域 (scope) (YAML，非必填)", 
            value=yaml.dump(rule.config.get('scope', {}), allow_unicode=True).rstrip('\n'), 
            key=f"{base_key}_scope",
            height=80,
        )
        try:
            cfg['scope'] = yaml.safe_load(scope_raw) if scope_raw.strip() else {}
        except Exception as e:
            st.warning(f"作用域配置解析失败，将使用空配置: {e}")
            cfg['scope'] = {}
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_scope_content = """
                node_selector:
                  kubernetes.io/os: linux
            """
            st.code(yaml_scope_content, language="yaml", line_numbers=False)
    # ===== Prometheus规则 =====
    elif rule.type == 'prometheus':
        # PromQL查询
        cfg['query'] = st.text_area(
            "Prometheus 查询 (PromQL)", 
            value=rule.config.get('query', ''), 
            key=f"{base_key}_query",
            height=68
        )
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_query_content = """
                (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
            """
            st.code(yaml_query_content, language="promql", line_numbers=False)
        # # 时间范围
        # time_range_raw = st.text_area(
        #     "时间范围 (time_range) (YAML，非必填)", 
        #     value=yaml.dump(rule.config.get('time_range', {}), allow_unicode=True).rstrip('\n'), 
        #     key=f"{base_key}_time_range",
        #     height=100
        # )
        # try:
        #     cfg['time_range'] = yaml.safe_load(time_range_raw) if time_range_raw.strip() else {}
        # except Exception as e:
        #     st.warning(f"时间范围解析失败，将使用空配置: {e}")
        #     cfg['time_range'] = {}
        # with st.expander("配置示例（点击展开）", expanded=False):
        #     yaml_time_range_content = """
        #         end: now
        #         start: now-10m
        #         step: 1m
        #     """
        #     st.code(yaml_time_range_content, language="yaml", line_numbers=False)
        # 断言配置
        assertions_raw = st.text_area(
            "断言配置 (YAML)", 
            value=yaml.dump(rule.config.get('assertions', {}), allow_unicode=True).rstrip('\n'), 
            key=f"{base_key}_assertions",
            height=128
        )
        try:
            cfg['assertions'] = yaml.safe_load(assertions_raw) if assertions_raw.strip() else {}
        except Exception as e:
            st.warning(f"断言配置解析失败，将使用空配置: {e}")
            cfg['assertions'] = {}
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_assertions_content = """
                - condition: max_value < 95
                  description: '节点内存使用率: {{ max_value | round(2) }}%'
                  name: 节点内存使用率严重告警
                  severity: critical        
            """
            st.code(yaml_assertions_content, language="yaml", line_numbers=False)
    # ===== OPA规则（核心修改：仅保留inline，移除file相关功能）=====
    elif rule.type == 'opa':
        # 资源列表
        resources_raw = st.text_area(
            "资源列表 (resources) (YAML，非必填)", 
            value=yaml.dump(rule.config.get('resources', []), allow_unicode=True).rstrip('\n'), 
            key=f"{base_key}_resources",
            height=80
        )
        try:
            cfg['resources'] = yaml.safe_load(resources_raw) if resources_raw.strip() else []
        except Exception as e:
            st.warning(f"资源列表解析失败，将使用空列表: {e}")
            cfg['resources'] = []
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_resources_content = """
                - apiVersion: v1
                  kind: Pod
                  namespaced: true
                - apiVersion: apps/v1
                  kind: StatefulSet
                  namespaced: true
                - apiVersion: apps/v1
                  kind: DaemonSet
                  namespaced: true
                - apiVersion: apps/v1
                  kind: Deployment
                  namespaced: true
            """
            st.code(yaml_resources_content, language="yaml", line_numbers=False)        
        # Rego配置
        st.markdown("Rego 配置")
        rego_default = rule.config.get('rego', {})
        # 直接读取inline值，无切换选项
        inline_raw = st.text_area(
            "内联 Rego 代码 *",  # 加*标记必填，符合OPA规则校验逻辑
            value=rego_default.get('inline', ''), 
            key=f"{base_key}_rego_inline",
            height=160,
            help="请输入完整的Rego规则代码，这是OPA规则的核心逻辑"
        )
        # 只保存inline字段，无file字段
        cfg['rego'] = {'inline': inline_raw}
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_rego_inline_content = """
                # 资源限制检查示例
                package kubernetes
                # 获取Pod规范
                get_pod_spec(resource) = spec if {
                    resource.kind == "Pod"
                    spec := resource.spec
                }
                get_pod_spec(resource) = spec if {
                    resource.kind != "Pod"
                    spec := resource.spec.template.spec
                }
                # 检查容器是否缺少资源限制
                missing_resources_containers(containers, field) = missing if {
                    missing := [container |
                        container := containers[_]
                        resources := object.get(container, "resources", {})
                        not resources[field]
                    ]
                }
                # 定义违规 - 缺少资源请求
                violations contains result if {
                    resource := input.resources[_]
                    spec := get_pod_spec(resource)
                    containers := array.concat(
                        default_array(spec.containers),
                        default_array(spec.initContainers)
                    )
                    missing_requests := missing_resources_containers(containers, "requests")
                    count(missing_requests) > 0
                    result := {
                        "kind": resource.kind,
                        "name": resource.metadata.name,
                        "namespace": resource.metadata.namespace,
                        "message": sprintf("%s '%s' in namespace '%s' has %d container(s) without resource requests: %s", [
                            resource.kind,
                            resource.metadata.name,
                            resource.metadata.namespace,
                            count(missing_requests),
                            concat(", ", [c.name | c := missing_requests[_]])
                        ])
                    }
                }
                # 定义违规 - 缺少资源限制
                violations contains result if {
                    resource := input.resources[_]
                    spec := get_pod_spec(resource)
                    containers := array.concat(
                        default_array(spec.containers), 
                        default_array(spec.initContainers)
                    )
                    missing_limits := missing_resources_containers(containers, "limits")
                    count(missing_limits) > 0
                    result := {
                        "kind": resource.kind,
                        "name": resource.metadata.name,
                        "namespace": resource.metadata.namespace,
                        "message": sprintf("%s '%s' in namespace '%s' has %d container(s) without resource limits: %s", [
                            resource.kind,
                            resource.metadata.name,
                            resource.metadata.namespace,
                            count(missing_limits),
                            concat(", ", [c.name | c := missing_limits[_]])
                        ])
                    }
                }
                # 辅助函数 - 返回默认空数组
                default_array(val) = result if {
                    val != null
                    result = val
                }
                default_array(val) = [] if {
                    val == null
                }
            """
            st.code(yaml_rego_inline_content, language="rego", line_numbers=False)
        # 断言配置
        assertions_raw = st.text_area(
            "断言配置 (YAML)", 
            value=yaml.dump(rule.config.get('assertions', {}), allow_unicode=True).rstrip('\n'), 
            key=f"{base_key}_assertions",
            height=128
        )
        try:
            cfg['assertions'] = yaml.safe_load(assertions_raw) if assertions_raw.strip() else {}
        except Exception as e:
            st.warning(f"断言配置解析失败，将使用空配置: {e}")
            cfg['assertions'] = {}
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_assertions_content = """
                - condition: violation_count == 0
                  description: 发现 {{ violation_count }} 个资源没有正确配置资源请求/限制
                  name: 检查是否有缺少资源配置的工作负载
                  severity: warning
                - condition: violation_count < 10
                  description: 发现大量 ({{ violation_count }}) 资源没有正确配置资源请求/限制
                  name: 检查是否有大量缺少资源配置的工作负载
                  severity: critical
            """
            st.code(yaml_assertions_content, language="yaml", line_numbers=False) 
        # Scope作用域（核心：实时读取）
        scope_raw = st.text_area(
            "作用域 (scope) (YAML，非必填)", 
            value=yaml.dump(rule.config.get('scope', {}), allow_unicode=True).rstrip('\n'), 
            key=f"{base_key}_scope",
            height=128,
            help="格式要求：{namespaces: {include: [命名空间1, 命名空间2], exclude: [命名空间3]}}，例如：\nnamespaces:\n  include: [default, kube-system]\n  exclude: [kube-public]"
        )
        try:
            cfg['scope'] = yaml.safe_load(scope_raw) if scope_raw.strip() else {}
        except Exception as e:
            st.warning(f"作用域配置解析失败，将使用空配置: {e}")
            cfg['scope'] = {}
        with st.expander("配置示例（点击展开）", expanded=False):
            yaml_scope_content = """
                namespaces:
                  exclude:
                    - kube-system
                    - kube-public
                  include: []
            """
            st.code(yaml_scope_content, language="yaml", line_numbers=False)
    # 直接返回实时配置，无任何缓存中转
    return cfg

def render_rule_detail(rule: Rule) -> None:
    """
    规则详情渲染
    """
    # 预编译所有配置，减少重复计算
    config = getattr(rule, 'config', {}) or {}
    rule_type = rule.type
    
    # 定义各类型的展示配置（批量处理，减少条件判断）
    display_configs = {
        "node": {
            "keys": ["execution", "assertions", "scope"],
            "labels": ["执行配置", "断言配置", "作用域配置"],
            "special": {"scope": ["node_selector"]}
        },
        "opa": {
            "keys": ["resources", "rego", "assertions", "scope"],
            "labels": ["资源配置", "Rego 规则配置", "断言配置", "作用域配置"],
            "special": {"scope": ["namespaces"], "rego": ["inline", "file"]}
        },
        "prometheus": {
            "keys": ["query", "time_range", "assertions"],
            "labels": ["Prometheus 查询", "时间范围配置", "断言配置"],
            "special": {"query": ["promql"]}
        }
    }
    
    if rule_type not in display_configs:
        st.markdown("⚠️ 不支持的规则类型")
        return
    
    cfg = display_configs[rule_type]
    all_displayed_keys = set()
    
    # 批量渲染核心配置（减少组件数量）
    for key, label in zip(cfg["keys"], cfg["labels"]):
        # 优先从rule属性取，没有则从config取
        value = getattr(rule, key, None) or config.get(key, None)
        if not value:
            continue
        
        all_displayed_keys.add(key)
        st.markdown(f"* **{label}**")
        
        # 特殊处理（极简版）
        if key in cfg["special"]:
            if key == "rego":
                # Rego 特殊处理（合并渲染）
                if isinstance(value, dict):
                    rego_content = ""
                    if "inline" in value:
                        rego_content = value["inline"]
                        st.markdown("**内联 Rego 代码:**")
                        st.code(rego_content, language="rego", line_numbers=False)  # 关闭行号减少渲染
                    if "file" in value:
                        st.markdown(f"**Rego 文件:** `{value['file']}`")
                else:
                    st.json(value, expanded=False)  # 关闭自动展开
            elif key == "scope":
                # 作用域特殊处理（合并JSON）
                st.json(value, expanded=False)
                # 子项极简渲染
                for sub_key in cfg["special"][key]:
                    sub_value = value.get(sub_key, None)
                    if sub_value:
                        if sub_key == "node_selector":
                            st.markdown("* **节点标签选择器**")
                            st.code(yaml.dump(sub_value, allow_unicode=True), language="yaml", line_numbers=False)
                        elif sub_key == "namespaces":
                            st.markdown("   * **命名空间配置**")
                            include = sub_value.get('include', [])
                            exclude = sub_value.get('exclude', [])
                            if include:
                                st.info(f"包含: {', '.join(include) if include else '全部'}")
                            if exclude:
                                st.warning(f"排除: {', '.join(exclude)}")
            elif key == "query":
                # PromQL 极简渲染
                st.code(value, language="promql", line_numbers=False)
        else:
            # 普通配置：合并JSON渲染，关闭自动展开
            st.json(value, expanded=False)
    
    # 剩余配置：批量渲染，只渲染一次
    remaining_config = {k: v for k, v in config.items() if k not in all_displayed_keys}
    if remaining_config:
        st.divider()
        st.markdown("**其他配置:**")
        st.json(remaining_config, expanded=False)

def create_rule_view( rule_type: str, key_suffix: str = "", rules: Optional[List[Rule]] = None, use_expanders: bool = False) -> None:
    """
    为规则管理页面提供一个不带复选框的查看/编辑列表。
    每条规则以一行显示，右侧有一个“查看/编辑”按钮，点击后通过 session_state 切换到详情页。
    参数:
        rule_type: 规则类型 ('node'|'prometheus'|'opa')
        key_suffix: 用于按钮 key 的后缀，避免冲突
        use_expanders: 如果为 True，则每条规则使用一个可展开的 expander 显示详细信息
    返回: None（直接在 Streamlit 页面上渲染）
    """
    if rules is None:
        rules = cached_load_rules_sorted(rule_type, include_disabled=True, signature=_rules_signature(rule_type))
    if not rules:
        st.info(f"没有找到任何 {rule_type} 规则。")
        return
    if use_expanders:
        # 使用 expander 为每条规则显示可展开的详细信息
        for rule in rules:
            title = f"{rule.id} — {rule.name}"
            with st.expander(title, expanded=False):
                cols = st.columns([2, 3.5, 1, 0.9, 0.9, 1])
                # ID 列
                with cols[0]:
                    st.markdown(f"**{rule.id}**")
                # 名称 + 完整或简短描述
                with cols[1]:
                    st.markdown(f"**{rule.name}**")
                    if getattr(rule, 'description', None):
                        st.caption(rule.description)
                # 类型
                with cols[2]:
                    type_map = {"node": "🖥️ 节点", "prometheus": "📊 监控", "opa": "🔒 安全"}
                    st.markdown(type_map.get(rule.type, rule.type))
                # 状态
                with cols[3]:
                    status_icon = "✅" if getattr(rule, 'enabled', False) else "❌"
                    st.markdown(f"{status_icon} {'启用' if getattr(rule, 'enabled', False) else '禁用'}")
                # 严重性
                with cols[4]:
                    st.markdown(getattr(rule, 'severity', ''))
                # 类别
                with cols[5]:
                    st.markdown(rule.category if getattr(rule, 'category', None) else "-")
                # 在 expander 内显示更详细的配置/断言信息
                st.divider()
                render_rule_detail(rule)
    else:
        # 渲染表头
        header_cols = st.columns([2, 3.5, 1, 0.9, 0.9, 1])
        headers = ["ID", "名称 / 描述", "类型", "状态", "严重性", "类别"]
        for hc, h in zip(header_cols, headers):
            hc.markdown(f"**{h}**")
        st.markdown("<hr style='border-top:4px solid #e6e6e6;margin:1px 0'/>", unsafe_allow_html=True)
        for idx, rule in enumerate(rules):
            cols = st.columns([2, 3.5, 1, 0.9, 0.9, 1])
            # ID 列
            with cols[0]:
                st.markdown(f"**{rule.id}**")
            # 名称 + 简短描述
            with cols[1]:
                st.markdown(f"**{rule.name}**")
                if getattr(rule, 'description', None):
                    short_desc = rule.description if len(rule.description) <= 80 else rule.description[:77] + '...'
                    st.caption(short_desc)
            # 类型
            with cols[2]:
                type_map = {"node": "🖥️ 节点", "prometheus": "📊 监控", "opa": "🔒 安全"}
                st.markdown(type_map.get(rule.type, rule.type))
            # 状态
            with cols[3]:
                status_icon = "✅" if getattr(rule, 'enabled', False) else "❌"
                st.markdown(f"{status_icon} {'启用' if getattr(rule, 'enabled', False) else '禁用'}")
            # 严重性
            with cols[4]:
                st.markdown(getattr(rule, 'severity', ''))
            # 类别
            with cols[5]:
                st.markdown(rule.category if getattr(rule, 'category', None) else "-")
            st.markdown("<hr style='border-top:1px solid #e6e6e6;margin:1px 0'/>", unsafe_allow_html=True)

def create_rule_view_tabs(
    node_check: bool, prometheus_check: bool, opa_check: bool, key_suffix: str = "",
    rules_by_type: Optional[Dict[str, List[Rule]]] = None, use_expanders: bool = False
) -> None:
    """
    按规则类型创建选项卡式的查看列表（不带复选框）。
    适用于规则管理的“查看/编辑”视图，不会返回已选规则列表，而是直接在页面渲染按钮。
    """
    rule_configs = [
        {"available": node_check, "type": "node", "tab_label": "节点巡检规则"},
        {"available": prometheus_check, "type": "prometheus", "tab_label": "Prometheus巡检规则"},
        {"available": opa_check, "type": "opa", "tab_label": "OPA巡检规则"}
    ]
    
    available_configs = [cfg for cfg in rule_configs if cfg["available"]]
    if not available_configs:
        st.warning("没有可用的巡检类型。")
        return
    # 为避免与页面顶部的“规则类型”选择重复，这里采用按类型分组的方式渲染列表（而不是再次创建选项卡）
    for cfg in available_configs:
        # 如果调用方传入了按类型分组的 rules_by_type，则使用之（以支持筛选后的显示）
        provided_rules = None
        if rules_by_type and cfg['type'] in rules_by_type:
            provided_rules = rules_by_type[cfg['type']]
        st.markdown(f"#### {cfg['tab_label']} ({len(provided_rules) if provided_rules is not None else '加载中...'})")
        create_rule_view(cfg["type"], key_suffix=f"{key_suffix}_{cfg['type']}", rules=provided_rules, use_expanders=use_expanders)
        st.divider()

def display_create_rule():
    st.markdown("### ➕ 创建新规则")
    # 初始化创建状态（极简，无冗余缓存）
    if 'create_state' not in st.session_state:
        st.session_state['create_state'] = {
            'type': 'node', 'id': '', 'name': '', 'category': '', 
            'severity': 'info', 'enabled': True, 'tier': 'basic',
            'desc': '', 'solution': '', 'tags': ''
        }
    state = st.session_state['create_state']

    # ===== 规则类型切换时触发rerun，确保界面实时更新 =====
    col_type, _ = st.columns([1, 4])
    with col_type:
        new_rule_type = st.selectbox(
            "规则类型", ['node', 'prometheus', 'opa'], 
            index=['node','prometheus','opa'].index(state['type']), 
            key="create_rule_type",
            on_change=lambda: st.session_state['create_state'].update({'type': st.session_state.create_rule_type})
        )
        state['type'] = new_rule_type

    # ===== 核心：单个form包裹所有内容，保证值能读取 =====
    with st.form("create_rule_form", clear_on_submit=False):
        # 基础信息列（移除原有的rule_type选择器，移到表单外）
        col1, col2 = st.columns(2)
        with col1:
            state['id'] = st.text_input(
                "规则ID *", state['id'], key="create_rule_id", 
                placeholder="唯一ID，无空格/斜杠，如：node_mem_limit"
            )
            state['name'] = st.text_input(
                "规则名称 *", state['name'], key="create_rule_name", 
                placeholder="如：节点内存资源限制检查"
            )
            state['category'] = st.text_input(
                "类别", state['category'], key="create_rule_category", 
                placeholder="如：storages、cpu、memory、process等"
            )
        with col2:
            sev_opts = ['info', 'low', 'warning', 'medium', 'high', 'critical']
            state['severity'] = st.selectbox(
                "严重性", sev_opts, index=sev_opts.index(state['severity']), 
                key="create_rule_severity"
            )
            state['enabled'] = st.checkbox("启用", state['enabled'], key="create_rule_enabled")
            state['tier'] = st.selectbox(
                "层级", ['basic', 'standard', 'extended', 'cluster'], 
                index=['basic','standard','extended','cluster'].index(state['tier']), 
                key="create_rule_tier"
            )

        # 描述、解决方案、Tags
        state['desc'] = st.text_area(
            "规则描述 *", state['desc'], key="create_rule_desc", 
            height=80, placeholder="请说明规则检查的目的、范围、逻辑"
        )
        state['solution'] = st.text_area(
            "解决方案", state['solution'], key="create_rule_solution", 
            height=80, placeholder="规则触发后的修复步骤/建议"
        )
        state['tags'] = st.text_input(
            "标签(逗号分隔)", state['tags'], key="create_rule_tags", 
            placeholder="如：k8s,node,prometheus,opa,resource"
        )

        # 配置编辑器（核心：传递唯一key，保证实时值读取）
        st.divider()
        st.markdown("#### 规则配置 *")
        temp_rule = Rule({
            'id': f"temp-create-{state['type']}",
            'type': state['type'],
            'config': {}
        })
        final_cfg = render_rule_editor(temp_rule, key_suffix=f"create_{state['type']}")

        # ===== 核心调整：测试按钮+集群选择+保存按钮 同一行布局 =====
        st.divider()
        st.markdown("#### 操作区")
        col_test, col_cluster, col_save = st.columns([1, 2, 0.8])  # 三列布局：测试/集群/保存
        clusters = list_clusters()
        selected_cluster = None
        
        with col_test:
            # 测试按钮：无集群时禁用
            test_clicked = st.form_submit_button(
                "🚀 执行实时测试", 
                type="secondary",
                disabled=not clusters
            )
        
        with col_cluster:
            # 集群选择框：放在测试按钮旁，无集群时显示提示+禁用
            if clusters:
                selected_cluster = st.selectbox(
                    "选择测试集群", clusters, 
                    key="create_test_cluster_唯一key",
                    disabled=not clusters
                )
            else:
                st.selectbox(
                    "选择测试集群", ["无可用集群"], 
                    key="create_test_cluster_唯一key",
                    disabled=True
                )
                st.caption("⚠️ 请先在「集群配置」添加集群")
        
        with col_save:
            save_clicked = st.form_submit_button(
                "💾 保存新规则", 
                type="primary"
            )

        # ===== 测试逻辑（使用同行列选的集群）=====
        if test_clicked:
            # 调用通用校验函数
            is_valid, error_messages = validate_rule_config(
                rule_type=state['type'],
                rule_name=state['name'],
                rule_desc=state['desc'],
                rule_config=final_cfg
            )
            
            # 额外的ID校验（仅创建规则需要）
            if not state['id'].strip():
                error_messages.append("规则ID不能为空")
            
            # 校验失败提示
            if error_messages:
                show_validation_errors(error_messages)
            else:
                # 校验通过，执行测试
                tmp_id = f"tmp_create_{state['id'].strip()}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                try:
                    run_rule_test(
                        rule_id=state['id'].strip(),
                        rule_type=state['type'],
                        selected_cluster=selected_cluster,
                        tmp_id=tmp_id,
                        temp_config=final_cfg
                    )
                except Exception as e:
                    st.error(f"❌ 测试执行失败: {str(e)}")
                    # 清理临时文件
                    try:
                        tmp_fp = RULES_DIR / state['type'] / f"{tmp_id}.yaml"
                        if tmp_fp.exists(): tmp_fp.unlink()
                    except Exception as clean_e:
                        st.warning(f"清理临时文件失败: {clean_e}")
                        
        # ===== 保存逻辑 =====
        if save_clicked:
            # 调用通用校验函数
            is_valid, error_messages = validate_rule_config(
                rule_type=state['type'],
                rule_name=state['name'],
                rule_desc=state['desc'],
                rule_config=final_cfg
            )
            
            # 额外的ID校验（仅创建规则需要）
            if not state['id'].strip():
                error_messages.append("规则ID不能为空")
            
            # 校验失败提示
            if error_messages:
                show_validation_errors(error_messages)
            else:
                # 校验通过，执行保存
                try:
                    # 解析Tags为列表（去空、去空格）
                    tags_list = [t.strip() for t in state['tags'].split(',') if t.strip()]
                    # 构建新规则对象
                    new_rule = Rule({
                        'id': state['id'].strip(),
                        'name': state['name'].strip(),
                        'type': state['type'],
                        'category': state['category'].strip() if state['category'] else '',
                        'severity': state['severity'],
                        'enabled': state['enabled'],
                        'tier': state['tier'],
                        'description': state['desc'].strip(),
                        'solution': state['solution'].strip() if state['solution'] else '',
                        'tags': tags_list,
                        'config': final_cfg
                    })
                    # 保存规则到本地
                    if save_rule(new_rule):
                        st.success(f"✅ 规则「{state['name']}」创建成功，已保存到本地！")
                        st.session_state['create_state'] = {
                            'type': 'node', 'id': '', 'name': '', 'category': '', 
                            'severity': 'info', 'enabled': True, 'tier': 'basic',
                            'desc': '', 'solution': '', 'tags': ''
                        }
                        cached_load_rules.clear()
                        time.sleep(1.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 规则保存失败: {str(e)}")
                 
def display_edit_rule():
    st.markdown("### ✏️ 编辑现有规则")
    # 规则类型筛选
    sel_type = st.selectbox(
        "筛选规则类型", ["全部", "node", "prometheus", "opa"], 
        key="edit_rule_type_filter"
    )
    # 加载规则
    load_type = None if sel_type == "全部" else sel_type
    rules = cached_load_rules_sorted(load_type, include_disabled=True, signature=_rules_signature(load_type))
    if not rules:
        st.info("📭 暂无可用规则，请先在「创建规则」中添加")
        return

    # 选择要编辑的规则
    rule_options = [f"{r.type}/{r.id} - {r.name}" for r in rules]
    sel_rule_str = st.selectbox("选择要编辑的规则", rule_options, key="edit_rule_select")
    rule = rules[rule_options.index(sel_rule_str)]

    # ===== 单个form包裹所有编辑内容，保证值实时读取 =====
    with st.form(f"edit_rule_form_{rule.id}", clear_on_submit=False):
        st.markdown(f"#### 编辑 {rule.type.upper()} 规则：{rule.name}（ID：{rule.id}）")
        st.caption(f"当前状态：{'✅ 启用' if rule.enabled else '❌ 禁用'} | 严重性：{rule.severity} | 类别：{rule.category}")

        # 基础信息编辑
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("规则ID（不可修改）", rule.id, disabled=True, key=f"edit_rule_id_{rule.id}")
            rule_name = st.text_input(
                "规则名称 *", value=rule.name, 
                key=f"edit_rule_name_{rule.id}"
            )
            rule_category = st.text_input(
                "类别", value=rule.category if hasattr(rule, 'category') else '', 
                key=f"edit_rule_category_{rule.id}"
            )
        with col2:
            sev_opts = ['info', 'low', 'warning', 'medium', 'high', 'critical']
            sev_idx = sev_opts.index(rule.severity) if hasattr(rule, 'severity') and rule.severity in sev_opts else 0
            rule_severity = st.selectbox(
                "严重性", sev_opts, sev_idx, 
                key=f"edit_rule_severity_{rule.id}"
            )
            rule_enabled = st.checkbox(
                "启用", value=rule.enabled if hasattr(rule, 'enabled') else True, 
                key=f"edit_rule_enabled_{rule.id}"
            )
            rule_tier = st.selectbox(
                "层级", ['basic', 'standard', 'extended', 'cluster'], 
                index=['basic','standard','extended','cluster'].index(rule.tier) if hasattr(rule, 'tier') else 0,
                key=f"edit_rule_tier_{rule.id}"
            )

        # 描述、解决方案、Tags（完整保留，实时读取）
        rule_desc = st.text_area(
            "规则描述 *", value=rule.description if hasattr(rule, 'description') else '', 
            key=f"edit_rule_desc_{rule.id}", height=80
        )
        rule_solution = st.text_area(
            "解决方案", value=rule.solution if hasattr(rule, 'solution') else '', 
            key=f"edit_rule_solution_{rule.id}", height=80
        )
        rule_tags = st.text_input(
            "标签(逗号分隔)", 
            value=','.join(rule.tags) if hasattr(rule, 'tags') and rule.tags else '', 
            key=f"edit_rule_tags_{rule.id}",
            placeholder="如：k8s,node,prometheus,opa,resource"
        )

        # 配置编辑器（核心：实时读取修改后的配置）
        st.divider()
        st.markdown("#### 规则配置 *")
        final_cfg = render_rule_editor(rule, key_suffix=f"edit_{rule.id}")

        # ===== 核心调整：测试按钮+集群选择+保存按钮 同一行布局 =====
        st.divider()
        st.markdown("#### 操作区")
        col_test, col_cluster, col_save = st.columns([1, 2, 1])  # 三列布局和创建规则保持一致
        clusters = list_clusters()
        selected_cluster = None
        
        with col_test:
            # 测试按钮：无集群时禁用
            test_clicked = st.form_submit_button(
                "🚀 执行实时测试", 
                type="secondary",
                disabled=not clusters
            )
        
        with col_cluster:
            # 集群选择框：测试按钮旁，无集群时禁用+提示
            if clusters:
                selected_cluster = st.selectbox(
                    "选择测试集群", clusters, 
                    key=f"edit_test_cluster_{rule.id}",
                    disabled=not clusters
                )
            else:
                st.selectbox(
                    "选择测试集群", ["无可用集群"], 
                    key=f"edit_test_cluster_{rule.id}",
                    disabled=True
                )
                st.caption("⚠️ 请先在「集群配置」添加集群")
        
        with col_save:
            save_clicked = st.form_submit_button(
                "💾 保存修改", 
                type="primary"
            )

        # ===== 测试逻辑（使用同行列选的集群）=====
        if test_clicked:
            # 调用通用校验函数
            is_valid, error_messages = validate_rule_config(
                rule_type=rule.type,
                rule_name=rule_name,
                rule_desc=rule_desc,
                rule_config=final_cfg
            )
            
            # 校验失败提示
            if error_messages:
                show_validation_errors(error_messages)
            else:
                # 校验通过，执行测试
                tmp_id = f"tmp_edit_{rule.id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                try:
                    run_rule_test(
                        rule_id=rule.id,
                        rule_type=rule.type,
                        selected_cluster=selected_cluster,
                        tmp_id=tmp_id,
                        temp_config=final_cfg
                    )
                except Exception as e:
                    st.error(f"❌ 测试执行失败: {str(e)}")
                    # 清理临时文件
                    try:
                        tmp_fp = RULES_DIR / rule.type / f"{tmp_id}.yaml"
                        if tmp_fp.exists(): tmp_fp.unlink()
                    except Exception as clean_e:
                        st.warning(f"清理临时文件失败: {clean_e}")

        # ===== 保存逻辑 =====
        if save_clicked:
            # 调用通用校验函数
            is_valid, error_messages = validate_rule_config(
                rule_type=rule.type,
                rule_name=rule_name,
                rule_desc=rule_desc,
                rule_config=final_cfg
            )
            
            # 校验失败提示
            if error_messages:
                show_validation_errors(error_messages)
            else:
                # 校验通过，执行保存
                try:
                    # 解析Tags
                    tags_list = [t.strip() for t in rule_tags.split(',') if t.strip()]
                    # 构建更新后的规则对象
                    updated_rule = Rule({
                        'id': rule.id,
                        'name': rule_name.strip(),
                        'type': rule.type,
                        'category': rule_category.strip() if rule_category else '',
                        'severity': rule_severity,
                        'enabled': rule_enabled,
                        'tier': rule_tier,
                        'description': rule_desc.strip(),
                        'solution': rule_solution.strip() if rule_solution else '',
                        'tags': tags_list,
                        'config': final_cfg
                    })
                    # 覆盖保存现有规则
                    if save_rule(updated_rule):
                        st.success(f"✅ 规则「{rule_name}」修改保存成功！")
                        cached_load_rules.clear()
                        time.sleep(1.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 规则修改保存失败: {str(e)}")

def render_local_rule_list():
    """渲染本地规则列表"""
    st.markdown("### 📋 本地规则列表")
    
    # 筛选条件
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        rule_types = ["全部", "node", "prometheus", "opa"]
        selected_type = st.selectbox(
            "规则类型",
            rule_types,
            format_func=lambda x: {
                "全部": "📦 全部类型",
                "node": "🖥️ 节点规则",
                "prometheus": "📊 监控规则",
                "opa": "🔒 安全规则"
            }.get(x, x),
            key="rule_list_type_static"
        )
    
    with col2:
        status_filter = st.selectbox(
            "状态筛选",
            ["全部", "启用", "禁用"],
            format_func=lambda x: {
                "全部": "📋 全部状态",
                "启用": "✅ 已启用",
                "禁用": "❌ 已禁用"
            }.get(x, x),
            key="rule_list_status_static"
        )

    with col3:
        all_rules_for_sev = cached_load_rules(None, include_disabled=True, signature=_rules_signature(None))
        sev_set = []
        for r in all_rules_for_sev:
            sev = getattr(r, 'severity', None)
            if sev and sev not in sev_set:
                sev_set.append(sev)

        severity_options = ["全部"] + sev_set
        selected_severity = st.selectbox(
            "严重性",
            severity_options,
            format_func=lambda x: "📋 全部" if x == "全部" else str(x),
            key="rule_list_sev_static"
        )
    
    # 加载并筛选规则
    rule_type_filter = None if selected_type == "全部" else selected_type
    all_rules = cached_load_rules_sorted(rule_type_filter, include_disabled=True, signature=_rules_signature(rule_type_filter))
    
    if status_filter == "启用":
        all_rules = [r for r in all_rules if r.enabled]
    elif status_filter == "禁用":
        all_rules = [r for r in all_rules if not r.enabled]

    if selected_severity and selected_severity != "全部":
        all_rules = [r for r in all_rules if (getattr(r, 'severity', '').lower() == selected_severity.lower())]
    
    if not all_rules:
        st.info("📭 没有找到符合条件的规则")
        return

    # 按类型分组显示
    has_node = any(r.type == 'node' for r in all_rules)
    has_prom = any(r.type == 'prometheus' for r in all_rules)
    has_opa = any(r.type == 'opa' for r in all_rules)
    
    if selected_type == "全部":
        rules_by_type: Dict[str, List[Rule]] = {
            'node': [r for r in all_rules if r.type == 'node'],
            'prometheus': [r for r in all_rules if r.type == 'prometheus'],
            'opa': [r for r in all_rules if r.type == 'opa']
        }
        create_rule_view_tabs(
            node_check=has_node,
            prometheus_check=has_prom,
            opa_check=has_opa,
            key_suffix="_list",
            rules_by_type=rules_by_type,
            use_expanders=True
        )
    else:
        filtered_rules = [r for r in all_rules if r.type == selected_type]
        create_rule_view(selected_type, key_suffix="_list", rules=filtered_rules, use_expanders=True)

def render_mode_selector(gitops_manager: GitOpsRuleManager, config: Dict):
    """渲染模式选择器"""
    st.markdown("#### 🎯 规则管理模式")
    
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        current_mode = config.get("mode", "local")
        mode_options = {
            "local": "📁 本地模式",
            "gitops": "🔄 GitOps模式"
        }
        
        selected_mode = st.selectbox(
            "选择管理模式",
            options=list(mode_options.keys()),
            format_func=lambda x: mode_options[x],
            index=list(mode_options.keys()).index(current_mode)
        )
        
        if selected_mode != current_mode:
            config["mode"] = selected_mode
            gitops_manager.save_config(config)
            st.success(f"已切换到{mode_options[selected_mode]}")
            st.rerun()
    
    with col2:
        # 显示当前统计
        local_rules_count = sum(len(cached_load_rules(rt, include_disabled=True, signature=_rules_signature(rt))) for rt in ["node", "prometheus", "opa"])
        st.metric("本地规则", local_rules_count)
    
    with col3:
        # 快速操作
        if st.button("🔄 刷新", help="刷新规则列表"):
            st.rerun()

def render_local_mode(gitops_manager: GitOpsRuleManager):
    """渲染本地模式界面"""
    st.markdown("#### 📁 本地规则")
    
    # 本地模式标签页：列表、创建、编辑
    tab1, tab2, tab3 = st.tabs(["规则列表", "添加规则", "编辑规则"])
    with tab1:
        render_local_rule_list()
    with tab2:
        display_create_rule()
    with tab3:
        display_edit_rule()

def render_gitops_mode(gitops_manager: GitOpsRuleManager, config: Dict):
    """渲染GitOps模式界面"""
    st.markdown("#### 🔄 GitOps规则管理（待完善）")
    
    # 选项卡
    tab_manage, tab_browse = st.tabs(["📚 仓库管理", "🔍 规则浏览"])
    
    with tab_manage:
        render_repository_management(gitops_manager, config)
    
    with tab_browse:
        render_git_rule_browser(gitops_manager, config)

def render_repository_management(gitops_manager: GitOpsRuleManager, config: Dict):
    """渲染仓库管理"""
    current_repo = config.get("current_repository", None)
    
    if current_repo:
        # 当前仓库信息
        st.markdown("### 📋 当前仓库")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**名称:** {current_repo['name']}")
            st.markdown(f"**地址:** `{current_repo['url']}`")
            st.markdown(f"**分支:** `{current_repo['branch']}`")
            if current_repo.get('description'):
                st.markdown(f"**描述:** {current_repo['description']}")
        
        with col2:
            if st.button("🔄 同步仓库", type="primary"):
                sync_repository(gitops_manager, current_repo)
            
            if st.button("❌ 切换仓库"):
                config["current_repository"] = None
                gitops_manager.save_config(config)
                st.success("已清除当前仓库，请选择新仓库")
                st.rerun()
    
    else:
        # 仓库选择
        st.markdown("### 🌟 选择Git规则仓库")
        
        # 官方推荐
        official_repo = DEFAULT_RULE_REPOS[0]
        
        st.markdown("#### 🏆 官方推荐")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{official_repo['name']}**")
            st.markdown(f"地址: `{official_repo['url']}`")
            st.markdown(f"描述: {official_repo['description']}")
        
        with col2:
            if st.button("🚀 启用官方仓库", type="primary"):
                config["current_repository"] = official_repo.copy()
                gitops_manager.save_config(config)
                st.success("✅ 已启用官方仓库")
                st.rerun()

def render_git_rule_browser(gitops_manager: GitOpsRuleManager, config: Dict):
    """渲染Git规则浏览器"""
    current_repo = config.get("current_repository", None)
    
    if not current_repo:
        st.warning("💡 请先在'仓库管理'中启用一个Git仓库")
        return
    
    # 检查仓库状态
    repo_path = gitops_manager.git_rules_dir / current_repo["name"]
    if not repo_path.exists():
        st.warning(f"⚠️ 仓库 **{current_repo['name']}** 尚未同步")
        if st.button("🔄 立即同步", type="primary"):
            sync_repository(gitops_manager, current_repo)
        return
    
    # 加载规则
    git_rules = gitops_manager.get_repo_rules(current_repo["name"])
    
    if not git_rules:
        st.info("📭 该仓库中暂无规则文件")
        return
    
    st.success(f"📚 仓库: **{current_repo['name']}** | 共 **{len(git_rules)}** 个规则")
    
    # 简单的规则列表
    for i, rule in enumerate(git_rules):
        with st.expander(f"📋 {rule.name} ({rule.type})", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**描述:** {rule.description}")
                st.markdown(f"**类型:** {rule.type} | **严重性:** {rule.severity}")
            
            with col2:
                if st.button(f"📥 导入", key=f"import_{rule.id}_{i}", type="primary"):
                    if gitops_manager.sync_git_rule_to_local(rule, rule.type):
                        st.success("✅ 已导入到本地")
                        cached_load_rules.clear()
                        st.rerun()
                    else:
                        st.error("❌ 导入失败")

def sync_repository(gitops_manager: GitOpsRuleManager, repo: Dict):
    """同步单个仓库"""
    with st.spinner(f"正在同步仓库 {repo['name']}..."):
        success, message = gitops_manager.clone_or_update_repo(
            repo["url"], 
            repo["name"], 
            repo.get("branch", "main")
        )
        
        if success:
            st.success(message)
            rules_count = len(gitops_manager.get_repo_rules(repo["name"]))
            st.info(f"发现 {rules_count} 个规则")
        else:
            st.error(message)
        
        # st.rerun()

def render_rule_management_tab():
    """渲染规则管理主标签页"""
    st.markdown("### 🛠️ 规则管理中心")

    gitops_manager = GitOpsRuleManager()
    config = gitops_manager.load_config()

    # 模式选择器
    render_mode_selector(gitops_manager, config)

    # 根据模式显示不同的界面
    if config["mode"] == "local":
        render_local_mode(gitops_manager)
    else:
        render_gitops_mode(gitops_manager, config)