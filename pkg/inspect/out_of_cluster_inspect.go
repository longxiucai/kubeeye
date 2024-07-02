package inspect

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"strings"

	"github.com/kubesphere/event-rule-engine/visitor"
	kubeeyev1alpha2 "github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"
	"github.com/kubesphere/kubeeye/pkg/conf"
	"github.com/kubesphere/kubeeye/pkg/constant"
	"github.com/kubesphere/kubeeye/pkg/kube"
	"github.com/kubesphere/kubeeye/pkg/ssh"
	"github.com/kubesphere/kubeeye/pkg/utils"

	"gopkg.in/yaml.v2"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/informers"
	"k8s.io/klog/v2"
)

type outOfClusterInspect struct {
}

func init() {
	RuleOperatorMap[constant.OutOfCluster] = &outOfClusterInspect{}
}

// type Cluster struct {
// 	Spec ClusterSpec `json:"spec,omitempty"`
// }

func (c *outOfClusterInspect) RunInspect(ctx context.Context, rules []kubeeyev1alpha2.JobRule, clients *kube.KubernetesClient, currentJobName string, informers informers.SharedInformerFactory, ownerRef ...metav1.OwnerReference) ([]byte, error) {

	var outOfClusterResult []kubeeyev1alpha2.OutOfClusterResultItem

	_, exist, phase := utils.ArrayFinds(rules, func(m kubeeyev1alpha2.JobRule) bool {
		return m.JobName == currentJobName
	})

	if exist {
		var outOfClusterRules []kubeeyev1alpha2.OutOfClusterRule
		err := json.Unmarshal(phase.RunRule, &outOfClusterRules)
		if err != nil {
			klog.Error(err, " Failed to marshal kubeeye result")
			return nil, err
		}
		sshcm, err := clients.ClientSet.CoreV1().ConfigMaps(constant.DefaultNamespace).
			Get(ctx, constant.DefaultOutOfClusterSSHConfigMap, metav1.GetOptions{})
		if err != nil {
			klog.Errorf("failed to get ssh config, ssh config file do not exist. err:%s", err)
			return nil, err
		}
		dataConfig := sshcm.Data["config"]
		var sshInfo conf.ClusterSpec
		err = yaml.Unmarshal([]byte(dataConfig), &sshInfo)
		if err != nil {
			klog.Errorf("failed to unmarshal ssh config. err:%s ", err)
			return nil, err
		}
		klog.Info(sshInfo)

		for _, r := range outOfClusterRules {
			var nodeList []string
			if len(r.NodeSelects) != 0 {
				for _, role := range r.NodeSelects {
					nodeList = append(nodeList, sshInfo.GetIPSByRole(role)...)
				}
			}
			if len(r.Hosts) != 0 {
				nodeList = append(nodeList, r.Hosts...)
			}

			for _, nodeIP := range nodeList {
				// var ctl kubeeyev1alpha2.OutOfClusterResultItem
				ctl := kubeeyev1alpha2.OutOfClusterResultItem{
					BaseResult: kubeeyev1alpha2.BaseResult{Name: r.Name},
					Command:    r.Command,
					NodeIP:     nodeIP,
				}
				// ctl.BaseResult = kubeeyev1alpha2.BaseResult{Name: r.Name}
				// ctl.Command = r.Command
				// ctl.NodeIP = nodeIP

				ip := net.ParseIP(nodeIP)
				klog.Infof("ip=%v cmd=%v rule=%v", nodeIP, r.Command, r.Rule)
				sshClient, err := ssh.GetHostSSHClient(ip, &sshInfo)
				if err != nil {
					ctl.Value = fmt.Sprintf("get host's ssh client failed err:%s", err)
					ctl.Level = r.Level
					ctl.Assert = true
					klog.Infof("ctl:%v\n", ctl)
					outOfClusterResult = append(outOfClusterResult, ctl)
					continue
				}
				outputResult, err := sshClient.Cmd(ip, r.Command)
				if err != nil {
					ctl.Value = fmt.Sprintf("command execute failed: %s", err)
					ctl.Level = r.Level
					ctl.Assert = true
					klog.Infof("ctl:%v\n", ctl)
					outOfClusterResult = append(outOfClusterResult, ctl)
					continue
				}
				outputResultString := strings.TrimSpace(string(outputResult))
				err, res := visitor.EventRuleEvaluate(map[string]interface{}{"result": outputResultString}, r.Rule)
				if err != nil {
					ctl.Value = fmt.Sprintf("rule evaluate failed err:%s", err)
					ctl.Level = r.Level
					ctl.Assert = true
				} else {
					ctl.Value = outputResultString
					if res {
						ctl.Level = r.Level
					}
					ctl.Assert = !res
				}
				klog.Infof("ctl:%v\n", ctl)
				outOfClusterResult = append(outOfClusterResult, ctl)
			}
		}
	}
	klog.Infof("outOfClusterResult:%v", outOfClusterResult)
	marshal, err := json.Marshal(outOfClusterResult)
	if err != nil {
		klog.Errorf("failed to marshal outOfClusterResult. err:%s ", err)
		return nil, err
	}
	return marshal, nil
}

func (c *outOfClusterInspect) GetResult(runNodeName string, resultCm *corev1.ConfigMap, resultCr *kubeeyev1alpha2.InspectResult) (*kubeeyev1alpha2.InspectResult, error) {
	var outOfClusterResult []kubeeyev1alpha2.OutOfClusterResultItem
	json.Unmarshal(resultCm.BinaryData[constant.Data], &outOfClusterResult)
	// if err != nil {
	// 	klog.Error("failed to get result", err)
	// 	return nil, err
	// }
	if outOfClusterResult == nil {
		return resultCr, nil
	}
	// for i := range outOfClusterResult {
	// 	outOfClusterResult[i].NodeName = runNodeName
	// }
	resultCr.Spec.OutOfClusterResult = outOfClusterResult
	return resultCr, nil

}
