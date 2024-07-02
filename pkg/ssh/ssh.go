package ssh

import (
	"fmt"
	"net"
	"time"

	"github.com/kubesphere/kubeeye/pkg/conf"
	"k8s.io/klog/v2"

	"dario.cat/mergo"

	netUtils "github.com/kubesphere/kubeeye/pkg/utils/net"
)

type Interface interface {
	// CmdAsync exec command on remote host, and asynchronous return logs
	CmdAsync(host net.IP, cmd ...string) error
	// Cmd exec command on remote host, and return combined standard output and standard error
	Cmd(host net.IP, cmd string) ([]byte, error)
	// CmdToString exec command on remote host, and return spilt standard output and standard error
	CmdToString(host net.IP, cmd, spilt string) (string, error)

	Ping(host net.IP) error
}

type SSH struct {
	IsStdout     bool
	Encrypted    bool
	User         string
	Password     string
	Port         string
	PkFile       string
	PkPassword   string
	Timeout      *time.Duration
	LocalAddress []net.Addr
	// Fs           fs.Interface
}

func NewSSHClient(ssh *conf.SSH, isStdout bool) Interface {
	if ssh.User == "" {
		ssh.User = "root"
	}
	address, err := netUtils.GetLocalHostAddresses()
	if err != nil {
		klog.Warningf("failed to get local address: %v", err)
	}
	return &SSH{
		IsStdout:     isStdout,
		Encrypted:    ssh.Encrypted,
		User:         ssh.User,
		Password:     ssh.Passwd,
		Port:         ssh.Port,
		PkFile:       ssh.Pk,
		PkPassword:   ssh.PkPasswd,
		LocalAddress: address,
		// Fs:           fs.NewFilesystem(),
	}
}

// GetHostSSHClient is used to executed bash command and no std out to be printed.
func GetHostSSHClient(hostIP net.IP, sshConfig *conf.ClusterSpec) (Interface, error) {
	for _, host := range sshConfig.Hosts {
		for _, ip := range host.IPS {
			if hostIP.Equal(net.ParseIP(ip)) {
				if err := mergo.Merge(&host.SSH, &sshConfig.SSH); err != nil {
					return nil, err
				}
				return NewSSHClient(&host.SSH, false), nil
			}
		}
	}
	return nil, fmt.Errorf("failed to get host ssh client: host ip %s not in hosts ip list", hostIP)
}

// NewStdoutSSHClient is used to show std out when execute bash command.
func NewStdoutSSHClient(hostIP net.IP, sshConfig *conf.ClusterSpec) (Interface, error) {
	for _, host := range sshConfig.Hosts {
		for _, ip := range host.IPS {
			if hostIP.Equal(net.ParseIP(ip)) {
				if err := mergo.Merge(&host.SSH, &sshConfig.SSH); err != nil {
					return nil, err
				}
				return NewSSHClient(&host.SSH, true), nil
			}
		}
	}
	return nil, fmt.Errorf("failed to get host ssh client: host ip %s not in hosts ip list", hostIP)
}
