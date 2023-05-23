/*
Copyright 2022.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controllers

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/kubesphere/kubeeye/constant"
	"github.com/kubesphere/kubeeye/pkg/kube"
	"github.com/kubesphere/kubeeye/pkg/utils"
	"github.com/pkg/errors"
	v1 "k8s.io/api/core/v1"
	"k8s.io/klog/v2"
	"strconv"
	"time"

	"github.com/robfig/cron/v3"
	kubeErr "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	kubeeyev1alpha2 "github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// InspectPlanReconciler reconciles a InspectPlan object
type InspectPlanReconciler struct {
	client.Client
	K8sClient *kube.KubernetesClient
	Scheme    *runtime.Scheme
}

const Finalizers = "kubeeye.finalizers.kubesphere.io"

//+kubebuilder:rbac:groups=kubeeye.kubesphere.io,resources=inspectplans,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=kubeeye.kubesphere.io,resources=inspectplans/status,verbs=get;update;patch
//+kubebuilder:rbac:groups=kubeeye.kubesphere.io,resources=inspectplans/finalizers,verbs=update

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
// TODO(user): Modify the Reconcile function to compare the state specified by
// the InspectPlan object against the actual cluster state, and then
// perform operations to make the cluster state reflect the state specified by
// the user.
//
// For more details, check Reconcile and its Result here:
// - https://pkg.go.dev/sigs.k8s.io/controller-runtime@v0.11.2/pkg/reconcile
func (r *InspectPlanReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {

	inspectPlan := &kubeeyev1alpha2.InspectPlan{}
	err := r.Get(ctx, req.NamespacedName, inspectPlan)
	if err != nil {
		if kubeErr.IsNotFound(err) {
			klog.Infof("inspect plan is not found;name:%s,namespect:%s\n", req.Name, req.Namespace)
			return ctrl.Result{}, nil
		}
		klog.Error("failed to get inspect plan.\n", err)
		return ctrl.Result{}, err
	}

	if inspectPlan.DeletionTimestamp.IsZero() {
		if _, b := utils.ArrayFind(Finalizers, inspectPlan.Finalizers); !b {
			inspectPlan.Finalizers = append(inspectPlan.Finalizers, Finalizers)
			err = r.Client.Update(ctx, inspectPlan)
			if err != nil {
				klog.Error("Failed to inspect plan add finalizers .\n", err)
				return ctrl.Result{}, err
			}
			return ctrl.Result{}, nil
		}

	} else {
		newFinalizers := utils.SliceRemove(Finalizers, inspectPlan.Finalizers)
		inspectPlan.Finalizers = newFinalizers.([]string)
		klog.Info("inspect plan is being deleted.")
		err = r.Client.Update(ctx, inspectPlan)
		if err != nil {
			klog.Error("Failed to inspect plan add finalizers.\n", err)
			return ctrl.Result{}, err
		}
		return ctrl.Result{}, nil
	}

	if inspectPlan.Spec.Suspend {
		klog.Info("inspect plan suspend")
		return ctrl.Result{}, nil
	}

	schedule, err := cron.ParseStandard(inspectPlan.Spec.Schedule)
	if err != nil {
		klog.Error("Unparseable schedule.\n", err)
		return ctrl.Result{}, nil
	}

	if inspectPlan.Spec.Timeout == "" {
		inspectPlan.Spec.Timeout = "10m"
	}

	now := time.Now()
	scheduledTime := nextScheduledTimeDuration(schedule, inspectPlan.Status.LastScheduleTime.Time)
	if inspectPlan.Status.LastScheduleTime.Add(*scheduledTime).Before(now) { // if the scheduled time has arrived, create Audit task

		taskName, err := r.createInspectTask(inspectPlan, ctx)
		if err != nil {
			klog.Error("failed to create InspectTask.", err)
			return ctrl.Result{}, err
		}
		klog.Error("create a new inspect task.", taskName)

		//if inspectPlan.Spec.MaxTasks > 0 {
		//	for len(inspectPlan.Status.TaskNames) > inspectPlan.Spec.MaxTasks-1 {
		//		for _, name := range inspectPlan.Status.TaskNames[0] {
		//			err = r.K8sClient.VersionClientSet.KubeeyeV1alpha2().InspectTasks(inspectPlan.GetNamespace()).Delete(ctx, name, metav1.DeleteOptions{})
		//
		//			if err == nil || kubeErr.IsNotFound(err) {
		//				inspectPlan.Status.TaskNames[0] = inspectPlan.Status.TaskNames[0][1:]
		//			} else {
		//				klog.Error("Failed to delete inspect task", err)
		//			}
		//		}
		//
		//	}
		//}

		inspectPlan.Status.LastScheduleTime = metav1.Time{Time: now}
		inspectPlan.Status.LastTaskName = taskName
		inspectPlan.Status.TaskNames = append(inspectPlan.Status.TaskNames, taskName)
		inspectPlan.Status.NextScheduleTime = metav1.Time{Time: schedule.Next(now)}
		err = r.Status().Update(ctx, inspectPlan)
		if err != nil {
			klog.Error("failed to update inspect plan.", err)
			return ctrl.Result{}, err
		}
		return ctrl.Result{RequeueAfter: 3 * time.Second}, nil
	} else {
		nextScheduledTime := nextScheduledTimeDuration(schedule, now)
		return ctrl.Result{RequeueAfter: *nextScheduledTime}, nil
	}
}

// SetupWithManager sets up the controller with the Manager.
func (r *InspectPlanReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&kubeeyev1alpha2.InspectPlan{}).
		Complete(r)
}

// nextScheduledTimeDuration returns the time duration to requeue based on
// the schedule and given time. It adds a 100ms padding to the next requeue to account
// for Network Time Protocol(NTP) time skews.
func nextScheduledTimeDuration(sched cron.Schedule, now time.Time) *time.Duration {
	nextTime := sched.Next(now).Add(100 * time.Millisecond).Sub(now)
	return &nextTime
}

func (r *InspectPlanReconciler) createInspectTask(inspectPlan *kubeeyev1alpha2.InspectPlan, ctx context.Context) (string, error) {
	ownerController := true
	ownerRef := metav1.OwnerReference{
		APIVersion:         inspectPlan.APIVersion,
		Kind:               inspectPlan.Kind,
		Name:               inspectPlan.Name,
		UID:                inspectPlan.UID,
		Controller:         &ownerController,
		BlockOwnerDeletion: &ownerController,
	}
	rules, err := r.scanRules(inspectPlan, ctx)
	if err != nil {
		return "", err
	}
	audits := inspectPlan.Spec.Auditors
	if len(audits) == 0 {
		audits = append(audits, kubeeyev1alpha2.AuditorKubeeye)
	}

	var inspectTask kubeeyev1alpha2.InspectTask
	inspectTask.Labels = map[string]string{constant.LabelName: inspectPlan.Name}
	inspectTask.OwnerReferences = []metav1.OwnerReference{ownerRef}
	inspectTask.Namespace = inspectPlan.Namespace
	inspectTask.Spec.Auditors = audits
	inspectTask.Spec.Timeout = inspectPlan.Spec.Timeout

	inspectTask.Spec.Rules = rules
	inspectTask.Name = fmt.Sprintf("%s-%s", inspectPlan.Name, strconv.Itoa(int(time.Now().Unix())))
	err = r.Client.Create(ctx, &inspectTask)
	if err != nil {
		klog.Error("create inspectTask failed", err)
		return "", err
	}

	return inspectTask.Name, nil
}

func (r *InspectPlanReconciler) scanRules(inspectPlan *kubeeyev1alpha2.InspectPlan, ctx context.Context) (map[string][]byte, error) {
	if len(inspectPlan.Spec.Tag) == 0 && len(inspectPlan.Spec.RuleNames) == 0 {
		return nil, errors.New("Failed to get tags and rule names")
	}

	selector := metav1.FormatLabelSelector(metav1.SetAsLabelSelector(map[string]string{constant.LabelRuleTag: inspectPlan.Spec.Tag}))
	ruleLists, err := r.K8sClient.VersionClientSet.KubeeyeV1alpha2().InspectRules(v1.NamespaceAll).List(ctx, metav1.ListOptions{LabelSelector: selector})
	if err != nil {
		if kubeErr.IsNotFound(err) {
			klog.Error("failed get to inspectrules not found.", err)
			return nil, err
		}
		klog.Error("failed get to inspectrules.", err)
		return nil, err
	}
	if ruleLists.Items == nil || len(ruleLists.Items) == 0 {
		klog.Errorf("Failed to  rules not found to tag:%s , check whether it exists", inspectPlan.Spec.Tag)
		return nil, errors.Errorf("Failed to  rules not found to tag:%s , check whether it exists", inspectPlan.Spec.Tag)
	}

	var resultRules = make(map[string][]byte)

	for _, item := range ruleLists.Items {

		if item.Spec.Opas != nil {
			var rules []kubeeyev1alpha2.OpaRule
			val, result := resultRules[constant.Opa]
			if result {
				json.Unmarshal(val, &result)
				//rules = val.([]kubeeyev1alpha2.OpaRule)
			}
			for _, opa := range item.Spec.Opas {
				rules = append(rules, opa)
			}
			marshal, _ := json.Marshal(rules)

			resultRules[constant.Opa] = marshal

		}
		if item.Spec.Prometheus != nil {
			var pro []kubeeyev1alpha2.PrometheusRule
			val, result := resultRules[constant.Prometheus]
			if result {
				json.Unmarshal(val, &pro)
				//pro = val.([]kubeeyev1alpha2.PrometheusRule)
			}
			for index := range item.Spec.Prometheus {
				if "" != item.Spec.PrometheusEndpoint && len(item.Spec.PrometheusEndpoint) > 0 {
					item.Spec.Prometheus[index].Endpoint = item.Spec.PrometheusEndpoint
				}
				pro = append(pro, item.Spec.Prometheus[index])
			}
			marshal, _ := json.Marshal(pro)
			resultRules[constant.Prometheus] = marshal
		}
		if item.Spec.FileChange != nil {
			var fileRule []kubeeyev1alpha2.FileChangeRule
			val, result := resultRules[constant.FileChange]
			if result {
				//rules = val.([]kubeeyev1alpha2.FileChangeRule)
				json.Unmarshal(val, &fileRule)
			}
			for _, fileChange := range item.Spec.FileChange {

				fileRule = append(fileRule, fileChange)
			}
			marshal, _ := json.Marshal(fileRule)
			resultRules[constant.FileChange] = marshal
		}
	}

	return resultRules, nil
}