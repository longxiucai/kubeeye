package plugins

import (
	"fmt"
	"io"
	"net/http"
	"time"

	"k8s.io/klog/v2"
)

func TriggerPluginsAudit(pluginList []string) {
	for _, pluginName := range pluginList {
		if CheckPluginsHealth(pluginName) {
			klog.Infof("trigger plugin %s inspect", pluginName)
			err, _ := TriggerAudit(pluginName)
			if err != nil {
				klog.Errorf("trigger plugin %s inspect failed", pluginName, err)
			}
			klog.Infof("trigger plugin %s inspect successful", pluginName)
		} else {
			klog.Errorf("plugin %s not ready", pluginName)
		}
	}
}

func CheckPluginsHealth(pluginName string) bool {
	_, err := http.Get(fmt.Sprintf("http://%s.kubeeye-system.svc/healthz", pluginName))

	return err == nil
}

func TriggerAudit(pluginName string) (error, []byte) {
	tr := &http.Transport{
		IdleConnTimeout:    5 * time.Second, // the maximum amount of time an idle connection will remain idle before closing itself.
		DisableCompression: true,            // prevents the Transport from requesting compression with an "Accept-Encoding: gzip" request header when the Request contains no existing Accept-Encoding value.
		WriteBufferSize:    10 << 10,        // specifies the size of the write buffer to 10KB used when writing to the transport.
	}
	client := &http.Client{Transport: tr}
	resp, err := client.Get(fmt.Sprintf("http://%s.kubeeye-system.svc/start", pluginName))
	if err != nil {
		return err, nil
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err, nil
	}

	return nil, body
}
