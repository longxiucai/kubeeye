package conf

import (
	"time"

	corev1 "k8s.io/api/core/v1"
)

const (
	AppsGroup                = "apps"
	NoGroup                  = ""
	BatchGroup               = "batch"
	RoleGroup                = "rbac.authorization.k8s.io"
	APIVersionV1             = "v1"
	Nodes                    = "nodes"
	Deployments              = "deployments"
	Pods                     = "pods"
	Daemonsets               = "daemonsets"
	Statefulsets             = "statefulsets"
	Jobs                     = "jobs"
	Cronjobs                 = "cronjobs"
	Namespaces               = "namespaces"
	Events                   = "events"
	Roles                    = "roles"
	Clusterroles             = "clusterroles"
	Group                    = "kubeeyeplugins.kubesphere.io"
	Version                  = "v1alpha1"
	Resource                 = "pluginsubscriptions"
	KubeeyeNameSpace         = "kubeeye-system"
	PluginInstalled   string = "installed"
	PluginPause       string = "pause"
	PluginInstalling  string = "installing"
	PluginUninstalled string = "uninstalled"
)

type KubeEyeConfig struct {
	Job     *JobConfig     `json:"job,omitempty"`
	Message *MessageConfig `json:"message,omitempty"`
}

type MessageType string

const (
	AlarmMessage MessageType = "alarm"
	EmailMessage MessageType = "email"
)

type Mode string

const (
	CompleteMode Mode = "complete"
	AbnormalMode Mode = "abnormal"
)

type MessageConfig struct {
	Enable bool        `json:"enable,omitempty"`
	Type   MessageType `json:"type,omitempty"`
	Mode   Mode        `json:"mode,omitempty"`
	Email  EmailConfig `json:"email,omitempty"`
}
type EmailConfig struct {
	Address   string   `json:"address,omitempty"`
	Port      int32    `json:"port,omitempty"`
	Fo        string   `json:"fo,omitempty"`
	To        []string `json:"to,omitempty"`
	SecretKey string   `json:"secretKey,omitempty"`
}

type JobConfig struct {
	ImageConfig  `json:",inline"`
	BackLimit    *int32                      `json:"backLimit,omitempty"`
	Resources    corev1.ResourceRequirements `json:"resources,omitempty"`
	AutoDelTime  *int32                      `json:"autoDelTime,omitempty"`
	MultiCluster map[string]ImageConfig      `json:"multiCluster,omitempty"`
}
type ImageConfig struct {
	Image           string `json:"image,omitempty"`
	ImagePullPolicy string `json:"imagePullPolicy,omitempty"`
}

func (k *KubeEyeConfig) GetClusterJobConfig(clusterName string) *JobConfig {
	if clusterName == "default" || k.Job.MultiCluster == nil {
		return k.Job
	}
	deepConfig := k.Job.DeepCopy()
	multiCluster, ok := k.Job.MultiCluster[clusterName]
	if !ok {
		return k.Job
	}
	deepConfig.Image = multiCluster.Image
	deepConfig.ImagePullPolicy = multiCluster.ImagePullPolicy
	return deepConfig
}

func (j *JobConfig) DeepCopy() *JobConfig {
	j2 := new(JobConfig)
	*j2 = *j
	return j2
}

type MessageEvent struct {
	Title     string
	Content   []byte
	Timestamp time.Time
}

type EventHandler interface {
	HandleMessageEvent(event *MessageEvent)
}

type SSH struct {
	Encrypted bool   `mapstructure:"encrypted" yaml:"encrypted,omitempty" json:"encrypted,omitempty"`
	User      string `mapstructure:"user" yaml:"user,omitempty" json:"user,omitempty"`
	Passwd    string `mapstructure:"passwd" yaml:"passwd,omitempty" json:"passwd,omitempty"`
	Pk        string `mapstructure:"pk" yaml:"pk,omitempty" json:"pk,omitempty"`
	PkPasswd  string `mapstructure:"pkPasswd" yaml:"pkPasswd,omitempty" json:"pkPasswd,omitempty"`
	Port      string `mapstructure:"port" yaml:"port,omitempty" json:"port,omitempty"`
}

type Host struct {
	IPS   []string `mapstructure:"ips" yaml:"ips,omitempty" json:"ips,omitempty"`
	Roles []string `mapstructure:"roles" yaml:"roles,omitempty" json:"roles,omitempty"`
	SSH   `mapstructure:"ssh" yaml:"ssh,omitempty" json:"ssh,omitempty"`
	Env   []string `mapstructure:"env" yaml:"env,omitempty" json:"env,omitempty"`
}

type ClusterSpec struct {
	Hosts []Host `mapstructure:"hosts" yaml:"hosts" json:"hosts"`
	SSH   `mapstructure:"ssh" yaml:"ssh,omitempty" json:"ssh,omitempty"`
}

func (in *ClusterSpec) GetIPSByRole(role string) []string {
	var hosts []string
	for _, host := range in.Hosts {
		for _, hostRole := range host.Roles {
			if role == hostRole {
				hosts = append(hosts, host.IPS...)
				continue
			}
		}
	}
	return hosts
}
