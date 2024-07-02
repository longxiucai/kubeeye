package ssh

import (
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/kubesphere/kubeeye/pkg/utils/hash"

	"github.com/pkg/sftp"
	"golang.org/x/crypto/ssh"
)

const DefaultSSHPort = "22"

func (s *SSH) connect(host net.IP) (*ssh.Client, error) {
	if s.Encrypted {
		passwd, err := hash.AesDecrypt([]byte(s.Password))
		if err != nil {
			return nil, err
		}
		s.Password = passwd
		s.Encrypted = false
	}
	auth := s.sshAuthMethod(s.Password, s.PkFile, s.PkPassword)
	config := ssh.Config{
		Ciphers: []string{"aes128-ctr", "aes192-ctr", "aes256-ctr", "aes128-gcm@openssh.com", "arcfour256", "arcfour128", "aes128-cbc", "3des-cbc", "aes192-cbc", "aes256-cbc"},
	}
	DefaultTimeout := time.Duration(15) * time.Second
	if s.Timeout == nil {
		s.Timeout = &DefaultTimeout
	}
	clientConfig := &ssh.ClientConfig{
		User:    s.User,
		Auth:    auth,
		Timeout: *s.Timeout,
		Config:  config,
		HostKeyCallback: func(hostname string, remote net.Addr, key ssh.PublicKey) error {
			return nil
		},
	}
	if s.Port == "" {
		s.Port = DefaultSSHPort
	}
	return ssh.Dial("tcp", fmt.Sprintf("%s:%s", host, s.Port), clientConfig)
}

func (s *SSH) Connect(host net.IP) (*ssh.Client, *ssh.Session, error) {
	client, err := s.connect(host)
	if err != nil {
		return nil, nil, err
	}

	session, err := client.NewSession()
	if err != nil {
		_ = client.Close()
		return nil, nil, err
	}

	modes := ssh.TerminalModes{
		ssh.ECHO:          0,     //disable echoing
		ssh.TTY_OP_ISPEED: 14400, // input speed = 14.4kbaud
		ssh.TTY_OP_OSPEED: 14400, // output speed = 14.4kbaud
	}

	if err := session.RequestPty("xterm", 80, 40, modes); err != nil {
		_ = session.Close()
		_ = client.Close()
		return nil, nil, err
	}

	return client, session, nil
}

func (s *SSH) sshAuthMethod(password, pkFile, pkPasswd string) (auth []ssh.AuthMethod) {
	if fileExist(pkFile) {
		am, err := s.sshPrivateKeyMethod(pkFile, pkPasswd)
		if err == nil {
			auth = append(auth, am)
		}
	}
	if password != "" {
		auth = append(auth, s.sshPasswordMethod(password))
	}
	return auth
}

// Authentication with a private key,private key has password and no password to verify in this
func (s *SSH) sshPrivateKeyMethod(pkFile, pkPassword string) (am ssh.AuthMethod, err error) {
	pkData, err := os.ReadFile(filepath.Clean(pkFile))
	if err != nil {
		return nil, err
	}

	var pk ssh.Signer
	if pkPassword == "" {
		pk, err = ssh.ParsePrivateKey(pkData)
		if err != nil {
			return nil, err
		}
	} else {
		bufPwd := []byte(pkPassword)
		pk, err = ssh.ParsePrivateKeyWithPassphrase(pkData, bufPwd)
		if err != nil {
			return nil, err
		}
	}
	return ssh.PublicKeys(pk), nil
}

func (s *SSH) sshPasswordMethod(password string) ssh.AuthMethod {
	return ssh.Password(password)
}

// func (s *SSH) sftpConnect(host net.IP) (*ssh.Client, *sftp.Client, error) {
// 	var (
// 		sshClient  *ssh.Client
// 		sftpClient *sftp.Client
// 		err        error
// 	)

// 	sshClient, err = s.connect(host)
// 	if err != nil {
// 		return nil, nil, err
// 	}

// 	// create sftp client
// 	if s.User != common.ROOT {
// 		sftpClient, err = s.NewSudoSftpClient(sshClient)
// 	} else {
// 		sftpClient, err = sftp.NewClient(sshClient)
// 	}

// 	return sshClient, sftpClient, err
// }

func (s *SSH) NewSudoSftpClient(conn *ssh.Client, opts ...sftp.ClientOption) (*sftp.Client, error) {
	var (
		cmd            string
		err            error
		ses, ses2      *ssh.Session
		buff           []byte
		sftpServerPath string
	)

	ses2, err = conn.NewSession()
	if err != nil {
		return nil, err
	}
	defer ses2.Close()

	cmd = `grep -oP "Subsystem\s+sftp\s+\K.*" /etc/ssh/sshd_config`
	buff, err = ses2.Output(cmd)
	if err != nil {
		return nil, fmt.Errorf("failed to execute cmd(%s): %v", cmd, err)
	}

	ses, err = conn.NewSession()
	if err != nil {
		return nil, err
	}

	sftpServerPath = strings.ReplaceAll(string(buff), "\r", "")
	if match, _ := regexp.MatchString(`^sudo `, sftpServerPath); !match {
		sftpServerPath = SUDO + sftpServerPath
	}

	ok, err := ses.SendRequest("exec", true, ssh.Marshal(struct{ Command string }{sftpServerPath}))
	if err == nil && !ok {
		return nil, errors.New("ssh: failed to exec request")
	}

	pw, err := ses.StdinPipe()
	if err != nil {
		return nil, err
	}
	pr, err := ses.StdoutPipe()
	if err != nil {
		return nil, err
	}

	return sftp.NewClientPipe(pr, pw, opts...)
}
