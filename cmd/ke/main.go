package main

import (
	"os"

	"github.com/kubesphere/kubeeye/cmd/ke/ctl"
	"k8s.io/klog/v2"
)

func main() {
	if err := ctl.Execute(); err != nil {
		klog.Error(err)
		os.Exit(1)
	}
}
