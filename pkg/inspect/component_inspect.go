package inspect

import (
	"context"
	"encoding/json"

	kubeeyev1alpha2 "github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"
	"github.com/kubesphere/kubeeye/pkg/constant"
	"github.com/kubesphere/kubeeye/pkg/kube"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/informers"
	"k8s.io/klog/v2"
)

type componentInspect struct {
}

func init() {
	RuleOperatorMap[constant.Component] = &componentInspect{}
}

func (c *componentInspect) RunInspect(ctx context.Context, rules []kubeeyev1alpha2.JobRule, clients *kube.KubernetesClient, currentJobName string, informers informers.SharedInformerFactory, ownerRef ...metav1.OwnerReference) ([]byte, error) {
	var componentResult []kubeeyev1alpha2.ComponentResultItem
	for _, namespace := range constant.SystemNamespaces {
		services, err := clients.ClientSet.CoreV1().Services(namespace).List(ctx, metav1.ListOptions{})
		if err == nil {
			for _, service := range services.Items {
				item := kubeeyev1alpha2.ComponentResultItem{BaseResult: kubeeyev1alpha2.BaseResult{
					Name: service.Name,
				}}
				if len(service.Spec.Selector) > 0 {
					pods, err := clients.ClientSet.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{LabelSelector: labels.FormatLabels(service.Spec.Selector)})
					if err == nil {
						for _, pod := range pods.Items {
							if pod.Status.Phase != corev1.PodRunning || !isAllContainersReady(&pod) {
								item.Assert = true
							}
						}
					} else {
						item.Assert = true
					}
					if item.Assert {
						item.Level = kubeeyev1alpha2.DangerLevel
					}
					componentResult = append(componentResult, item)
				}

			}
		}
	}
	marshal, err := json.Marshal(componentResult)
	if err != nil {
		return nil, err
	}

	return marshal, nil
}

func (c *componentInspect) GetResult(runNodeName string, resultCm *corev1.ConfigMap, resultCr *kubeeyev1alpha2.InspectResult) (*kubeeyev1alpha2.InspectResult, error) {
	var componentResult []kubeeyev1alpha2.ComponentResultItem
	var componentResultItem kubeeyev1alpha2.ComponentResultItem
	if resultCm == nil {
		klog.Infof("starting generate failed result data(job)")
		componentResultItem.Level = kubeeyev1alpha2.DangerLevel
		componentResultItem.Assert = true
		componentResultItem.Name = "[ERROR]component_job_failed_PLEASE_CHECK_THE_NODE"
		resultCr.Spec.ComponentResult = append(resultCr.Spec.ComponentResult, componentResultItem)
		return resultCr, nil
	}
	err := json.Unmarshal(resultCm.BinaryData[constant.Data], &componentResult)
	if err != nil {
		return nil, err
	}

	resultCr.Spec.ComponentResult = componentResult

	return resultCr, nil
}

func isAllContainersReady(pod *corev1.Pod) bool {
	for _, c := range pod.Status.ContainerStatuses {
		if c.Ready {
			return true
		}
	}
	return false
}
