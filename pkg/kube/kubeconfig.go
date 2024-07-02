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

package kube

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"github.com/ghodss/yaml"
	"github.com/kubesphere/kubeeye/clients/clientset/versioned"
	"github.com/kubesphere/kubeeye/pkg/conf"
	"github.com/kubesphere/kubeeye/pkg/constant"
	"github.com/pkg/errors"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/informers/core"
	"k8s.io/client-go/kubernetes"
	_ "k8s.io/client-go/plugin/pkg/client/auth"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/klog/v2"
	"sigs.k8s.io/controller-runtime/pkg/client/config"
)

//var KubeConfig *rest.Config

type KubernetesClient struct {
	KubeConfig       *rest.Config
	ClientSet        kubernetes.Interface
	VersionClientSet versioned.Interface
	DynamicClient    dynamic.Interface
}

// GetKubeConfig get the kubeconfig from path or by GetConfig
func GetKubeConfig(kubeconfigPath string) (*rest.Config, error) {
	var kubeConfig *rest.Config
	var err error
	if kubeconfigPath != "" {
		kubeConfig, err = clientcmd.BuildConfigFromFlags("", kubeconfigPath)
		if err != nil {
			kubeConfig, err = config.GetConfig()
			if err != nil {
				return nil, errors.Wrapf(err, "failed to load kubeconfig file from %v", kubeconfigPath)
			}
		}
	} else if kubeconfigPath == "" {
		kubeConfig, err = config.GetConfig()
		if err != nil {
			kubeConfig, err = rest.InClusterConfig()
			if err != nil {
				return nil, errors.Wrap(err, "failed to load kubeconfig file from $HOME/.kube/")
			}
		}
	}
	return kubeConfig, err
}

func GetKubeConfigInCluster() (*rest.Config, error) {
	kubeConfig, err := rest.InClusterConfig()
	if err != nil {
		kubeConfig, err = config.GetConfig()
		if err != nil {
			return nil, err
		}
	}
	return kubeConfig, nil
}

// K8SClients return kubeconfig clientset and dynamicClient.
func (k *KubernetesClient) K8SClients(kubeConfig *rest.Config) (*KubernetesClient, error) {
	clientSet, err := kubernetes.NewForConfig(kubeConfig)
	if err != nil {
		return nil, errors.Wrap(err, "failed to load clientSet")
	}

	dynamicClient, err := dynamic.NewForConfig(kubeConfig)
	if err != nil {
		return nil, errors.Wrap(err, "failed to load dynamicClient")
	}

	versionClientSet, err := versioned.NewForConfig(kubeConfig)
	if err != nil {
		return nil, errors.Wrap(err, "failed to load informersClient")
	}

	k.VersionClientSet = versionClientSet
	k.ClientSet = clientSet
	k.DynamicClient = dynamicClient
	k.KubeConfig = kubeConfig

	return k, nil
}

func GetK8SClients(kubeconfig string) (*KubernetesClient, error) {
	kubeConfig, err := GetKubeConfig(kubeconfig)
	if err != nil {
		return nil, errors.Wrap(err, "failed to load config file")
	}

	var kc KubernetesClient
	clients, err := kc.K8SClients(kubeConfig)
	if err != nil {
		return nil, err
	}
	return clients, nil
}
func GetMultiClusterClient(ctx context.Context, clients *KubernetesClient, clusterName string) (*KubernetesClient, error) {
	klog.Infof("starting get cluster config %s", clusterName)
	raw, err := clients.ClientSet.CoreV1().RESTClient().Get().AbsPath("/apis/cluster.kubesphere.io/v1alpha1/clusters/").Name(clusterName).DoRaw(ctx)
	if err != nil {
		klog.Error(err, "failed to get cluster config")
		return nil, err
	}
	var cluster map[string]interface{}
	err = json.Unmarshal(raw, &cluster)
	if err != nil {
		klog.Error(err, "failed to unmarshal cluster config")
		return nil, err
	}
	kubeConfig := cluster["spec"].(map[string]interface{})["connection"].(map[string]interface{})["kubeconfig"].(string)

	decodeString, err := base64.StdEncoding.DecodeString(kubeConfig)
	if err != nil {
		klog.Error(err, "failed to decode kubeconfig")
		return nil, err
	}

	clientCmdConfig, err := clientcmd.NewClientConfigFromBytes(decodeString)
	if err != nil {
		klog.Error(err, "failed to get client config")
		return nil, err
	}
	clientConfig, err := clientCmdConfig.ClientConfig()
	if err != nil {
		klog.Error(err)
		return nil, err
	}

	var kc KubernetesClient
	sClients, err := kc.K8SClients(clientConfig)
	if err != nil {
		klog.Error(err)
		return nil, err
	}

	return sClients, nil
}

func GetKubeEyeConfig(c core.Interface) (kc conf.KubeEyeConfig, err error) {
	kubeEyeCm, err := c.V1().ConfigMaps().Lister().ConfigMaps(constant.DefaultNamespace).Get("kubeeye-config")
	if err != nil {
		klog.Errorf("failed to get kubeeye config, kubeeye config file do not exist. err:%s", err)
		return kc, err
	}
	dataConfig := kubeEyeCm.Data["config"]

	err = yaml.Unmarshal([]byte(dataConfig), &kc)
	if err != nil {
		klog.Errorf("failed to unmarshal kubeeye config. err:%s ", err)
		return kc, err
	}
	return kc, nil
}
