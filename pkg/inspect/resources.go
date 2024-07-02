// Copyright 2020 KubeSphere Authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package inspect

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"
	"github.com/kubesphere/kubeeye/pkg/kube"
	"github.com/open-policy-agent/opa/rego"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/klog/v2"
	"net/http"
	"sync"
	"time"
)

var lock sync.Mutex

type validateFunc func(ctx context.Context, regoRulesList []string) []v1alpha2.ResourceResult

func RegoRulesValidate(queryRule string, Resources kube.K8SResource, auditPercent *PercentOutput) validateFunc {

	return func(ctx context.Context, regoRulesList []string) []v1alpha2.ResourceResult {
		var auditResults []v1alpha2.ResourceResult

		if queryRule == workloads && Resources.Namespaces != nil {
			for _, resource := range Resources.Namespaces.Items {
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == workloads && Resources.Deployments != nil {
			for _, resource := range Resources.Deployments.Items {
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == workloads && Resources.Pods != nil {
			for _, resource := range Resources.Pods.Items {
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == workloads && Resources.StatefulSets != nil {
			for _, resource := range Resources.StatefulSets.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == workloads && Resources.DaemonSets != nil {
			for _, resource := range Resources.DaemonSets.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == workloads && Resources.Jobs != nil {
			for _, resource := range Resources.Jobs.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == workloads && Resources.CronJobs != nil {
			for _, resource := range Resources.CronJobs.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == rbac && Resources.Roles != nil {
			for _, resource := range Resources.Roles.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == rbac && Resources.ClusterRoles != nil {
			for _, resource := range Resources.ClusterRoles.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == nodes && Resources.Nodes != nil {
			for _, resource := range Resources.Nodes.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == events && Resources.Events != nil {
			for _, resource := range Resources.Events.Items {
				lock.Lock()
				auditPercent.CurrentAuditCount--
				auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
				lock.Unlock()
				if auditResult, found := validateK8SResource(ctx, resource, regoRulesList, queryRule); found {
					auditResults = append(auditResults, auditResult)
				}
			}
		}
		if queryRule == certexp && Resources.APIServerAddress != "" {
			lock.Lock()
			auditPercent.CurrentAuditCount--
			auditPercent.AuditPercent = (auditPercent.TotalAuditCount - auditPercent.CurrentAuditCount) * 100 / auditPercent.TotalAuditCount
			lock.Unlock()
			resource := Resources.APIServerAddress
			if auditResult, found := validateCertExp(resource); found {
				auditResults = append(auditResults, auditResult)

			}
		}

		return auditResults
	}
}

// MergeRegoRulesValidate Validate kubernetes cluster Resources, put the results into channels.
func MergeRegoRulesValidate(ctx context.Context, regoRulesChan []string, vfuncs ...validateFunc) <-chan []v1alpha2.ResourceResult {

	resultChan := make(chan []v1alpha2.ResourceResult)
	var wg sync.WaitGroup
	wg.Add(len(vfuncs))

	mergeResult := func(ctx context.Context, vf validateFunc) {
		defer wg.Done()
		resultChan <- vf(ctx, regoRulesChan)
	}
	for _, vf := range vfuncs {
		go mergeResult(ctx, vf)
	}

	go func() {
		defer close(resultChan)
		wg.Wait()
	}()

	return resultChan
}

func VailOpaRulesResult(ctx context.Context, k8sResources kube.K8SResource, RegoRules []string) v1alpha2.KubeeyeOpaResult {
	klog.Info("start Opa rule inspect")
	auditPercent := &PercentOutput{}

	if k8sResources.Deployments != nil {
		auditPercent.TotalAuditCount += len(k8sResources.Deployments.Items)
	}
	if k8sResources.Pods != nil {
		auditPercent.TotalAuditCount += len(k8sResources.Pods.Items)
	}
	if k8sResources.StatefulSets != nil {
		auditPercent.TotalAuditCount += len(k8sResources.StatefulSets.Items)
	}
	if k8sResources.DaemonSets != nil {
		auditPercent.TotalAuditCount += len(k8sResources.DaemonSets.Items)
	}
	if k8sResources.Jobs != nil {
		auditPercent.TotalAuditCount += len(k8sResources.Jobs.Items)
	}
	if k8sResources.CronJobs != nil {
		auditPercent.TotalAuditCount += len(k8sResources.CronJobs.Items)
	}
	if k8sResources.Roles != nil {
		auditPercent.TotalAuditCount += len(k8sResources.Roles.Items)
	}
	if k8sResources.ClusterRoles != nil {
		auditPercent.TotalAuditCount += len(k8sResources.ClusterRoles.Items)
	}
	if k8sResources.Nodes != nil {
		auditPercent.TotalAuditCount += len(k8sResources.Nodes.Items)
	}
	if k8sResources.Events != nil {
		auditPercent.TotalAuditCount += len(k8sResources.Events.Items)
	}
	auditPercent.TotalAuditCount++
	auditPercent.CurrentAuditCount = auditPercent.TotalAuditCount

	//regoRulesChan := rules.MergeRegoRules(ctx, RegoRules, rules.GetAdditionalRegoRulesfiles(additionalregoruleputh))
	RulesValidateChan := MergeRegoRulesValidate(ctx, RegoRules,
		RegoRulesValidate(workloads, k8sResources, auditPercent),
		RegoRulesValidate(rbac, k8sResources, auditPercent),
		RegoRulesValidate(events, k8sResources, auditPercent),
		RegoRulesValidate(nodes, k8sResources, auditPercent),
		RegoRulesValidate(certexp, k8sResources, auditPercent),
	)
	klog.Info("get inspect results")

	RuleResult := v1alpha2.KubeeyeOpaResult{}
	var results []v1alpha2.ResourceResult
	ctxCancel, cancel := context.WithCancel(ctx)

	go func(ctx context.Context) {
		ticker := time.NewTicker(1 * time.Second)
		for {
			select {
			case <-ticker.C:
				RuleResult.Percent = auditPercent.AuditPercent // update kubeeye inspect percent
				ext := runtime.RawExtension{}
				marshal, err := json.Marshal(RuleResult)
				if err != nil {
					klog.Error(err, " failed marshal kubeeye result")
					return
				}
				ext.Raw = marshal
				//auditResult.Result = ext
			case <-ctx.Done():
				return
			}
		}
	}(ctxCancel)

	for r := range RulesValidateChan {

		results = append(results, r...)
	}

	cancel()
	scoreInfo := CalculateScore(results, k8sResources)
	RuleResult.Percent = 100
	RuleResult.ScoreInfo = scoreInfo
	RuleResult.ExtraInfo = v1alpha2.ExtraInfo{
		WorkloadsCount: k8sResources.WorkloadsCount,
		NamespacesList: k8sResources.NameSpacesList,
	}

	RuleResult.ResourceResults = results
	return RuleResult
}

// ValidateK8SResource validate kubernetes resource by rego, return the validate results.
func validateK8SResource(ctx context.Context, resource unstructured.Unstructured, regoRulesList []string, queryRule string) (v1alpha2.ResourceResult, bool) {
	var auditResult v1alpha2.ResourceResult
	var resultItems v1alpha2.ResultItem
	find := false
	for _, regoRule := range regoRulesList {
		query, err := rego.New(rego.Query(queryRule), rego.Module("examples.rego", regoRule)).PrepareForEval(ctx)
		if err != nil {

			klog.Errorf("failed to parse rego input: %s", err.Error())
			return v1alpha2.ResourceResult{}, false
		}
		regoResults, err := query.Eval(ctx, rego.EvalInput(resource))
		if err != nil {
			klog.Errorf("failed to validate resource: %s", err.Error())

			return v1alpha2.ResourceResult{}, false
		}
		for _, regoResult := range regoResults {
			for key := range regoResult.Expressions {
				for _, validateResult := range regoResult.Expressions[key].Value.(map[string]interface{}) {
					var results []kube.ValidateResult
					jsonresult, err := json.Marshal(validateResult)
					if err != nil {
						klog.Error(err)
						return v1alpha2.ResourceResult{}, false
					}
					if err := json.Unmarshal(jsonresult, &results); err != nil {
						klog.Error(err)
						return v1alpha2.ResourceResult{}, false
					}
					for _, result := range results {
						find = true
						if result.Type == "ClusterRole" || result.Type == "Node" {
							auditResult.Name = result.Name
							auditResult.ResourceType = result.Type
							resultItems.Level = result.Level
							resultItems.Message = result.Message
							resultItems.Reason = result.Reason

							auditResult.ResultItems = append(auditResult.ResultItems, resultItems)
						} else if result.Type == "Event" {
							auditResult.Name = result.Name
							auditResult.NameSpace = result.Namespace
							auditResult.ResourceType = result.Type
							resultItems.Level = result.Level
							resultItems.Message = result.Message
							resultItems.Reason = result.Reason

							auditResult.ResultItems = append(auditResult.ResultItems, resultItems)
						} else {
							auditResult.Name = result.Name
							auditResult.NameSpace = result.Namespace
							auditResult.ResourceType = result.Type
							resultItems.Level = result.Level
							resultItems.Message = result.Message
							resultItems.Reason = result.Reason

							auditResult.ResultItems = append(auditResult.ResultItems, resultItems)
						}
					}
				}
			}
		}
	}
	return auditResult, find
}

// validateCertExp validate kube-apiserver certificate expiration
func validateCertExp(ApiAddress string) (v1alpha2.ResourceResult, bool) {
	var auditResult v1alpha2.ResourceResult
	var resultItems v1alpha2.ResultItem
	var find bool
	resourceType := "Cert"

	if ApiAddress != "" {
		tr := &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		}
		client := &http.Client{Transport: tr}
		resp, err := client.Get(ApiAddress)
		if err != nil {
			find = false
			fmt.Printf("Failed to get Kubernetes kube-apiserver certificate expiration.\n")
			return auditResult, find
		}
		defer func() { _ = resp.Body.Close() }()

		for _, cert := range resp.TLS.PeerCertificates {
			expDate := int(cert.NotAfter.Sub(time.Now()).Hours() / 24)
			if expDate <= 30 {
				find = true
				auditResult.ResourceType = resourceType
				auditResult.Name = "certificateExpire"
				resultItems.Message = "CertificateExpiredPeriod"
				resultItems.Level = "dangerous"
				resultItems.Reason = "Certificate expiration time <= 30 days"
			}
		}
	}
	auditResult.ResultItems = append(auditResult.ResultItems, resultItems)
	return auditResult, find
}
