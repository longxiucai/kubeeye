package template

import (
	hemltemplate "html/template"
	texttemplate "text/template"
)

func GetInspectRuleTemplate() (*texttemplate.Template, error) {

	return texttemplate.New("examples-inspect-rule").Parse(`
apiVersion: kubeeye.kubesphere.io/v1alpha2
kind: InspectRule
metadata:
  labels:
    app.kubernetes.io/name: inspectrule
    app.kubernetes.io/instance: inspectrule-sample
    app.kubernetes.io/part-of: kubeeye
    app.kubernetes.io/managed-by: kustomize
    app.kubernetes.io/created-by: kubeeye
    kubeeye.kubesphere.io/rule-tag: kubeeye_workloads_rego
  name: inspect-rules-sample
  namespace: kubeeye-system
spec:
  sysctl:
    - name: vm.max_map_count
      rule: vm.max_map_count==262144      
      nodeName: master
      nodeSelector:
		kubernetes.io/name: ""
  systemd:
    - name: docker
      rule: docker = "active"
      nodeName: master
      nodeSelector:
		kubernetes.io/name: ""
  fileChange:
    - name: 
      path: 
      nodeName: master
      nodeSelector:
		kubernetes.io/name: ""
  prometheusEndpoint: 
  prometheus:
    - name: 
      rule: 
  opas:
    - module: kubeeye_workloads_rego
      name: 
      rule: |-
`)

}

func GetInspectPlanTemplate() (*texttemplate.Template, error) {
	return texttemplate.New("examples-inspect-plan").Parse(`
	apiVersion: kubeeye.kubesphere.io/v1alpha2
	kind: InspectPlan
	metadata:
	  name: inspect-plan-sample
	  namespace: kubeeye-system
	spec:
	  schedule: "*/30 * * *  ?"
	  maxTasks: 10
	  tag: kubeeye_workloads_rego
	`)
}

const InspectResultTemplate = "inspectResult.tpl"

func GetInspectResultHtmlTemplate() (*hemltemplate.Template, error) {
	return hemltemplate.New(InspectResultTemplate).Parse(`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>inspect report</title>
</head>
<body>

<div class="header">InspectReport（{{- .title -}}）</div>

<div class="content">
    <div style="font-size: 30px;min-width: 800px;">overview</div>
    <table border="1" cellpadding="0" cellspacing="0" class="overview">
        <thead>
        <tr>
            <td>ruleType</td>
            <td>inspectRuleNumber</td>
            <td>issuesNumber</td>
        </tr>
        </thead>
        <tbody>

        {{range .overview}}
        <tr>{{range $i,$v:= .}}
            {{if eq $i 0}}
            <td><a href="#{{.}}">{{.}}</a></td>
            {{else}}
            <td> {{.}}</td>
            {{end}}
            {{end}}
        </tr>
        {{end}}
        </tbody>
    </table>
</div>

{{range $k,$v:= .details}}

<div class="content">
    <div style="font-size: 30px;width: 100%"><a id="{{$k}}">{{$k}}</a></div>
<div class="table">
        {{range $i,$v1:=$v }}

    <div class="tr">
     
            {{range $v1.Children}}

            {{if $v1.Header}}
            <div class="td">{{.Text}}</div>
            {{else}}
            <div class="td">{{.Text}}</div>
            {{end}}
            {{end}}
        </div>

        {{end}}
</div>
</div>

{{end}}

</body>
<style>
    .header {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 50px;
        width: 100%;
        box-sizing: border-box;
        font-size: 50px;
        font-weight: bold;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        background-color: #f9f9f9;
    }

    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }

    th {
        background-color: #f2f2f2;
    }

    /* 页面内容样式 */
    .content {
        width: 80%;
        margin: 20px auto;
        background-color: #fff;
        border-radius: 5px;
        box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        padding: 20px;
    }

    .overview {
        min-width: 800px;
        text-align: center;
    }

    /* 全局样式 */
    body {
        font-family: Arial, sans-serif;
        background-color: #f0f0f0;
        margin: 0;
        padding: 0;
    }

    /* 表格样式 */
    .table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
    }

    .tr {
        width: 100%;
        display: flex;
        border: 1px solid #ddd;
        background-color: #f9f9f9;
    }

    .td {
        flex: 1;
        display: flex;
        flex-wrap: wrap;
        white-space: pre-wrap;
        border-right: 1px solid #ddd;
        word-break: break-all;
        padding: 3px;
    }
</style>

</html>
`)
}
