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
// Code generated by lister-gen. DO NOT EDIT.

package v1alpha1

import (
	v1alpha1 "github.com/kubesphere/kubeeye/api/kubeeye/v1alpha1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/tools/cache"
)

// AuditPlanLister helps list AuditPlans.
// All objects returned here must be treated as read-only.
type AuditPlanLister interface {
	// List lists all AuditPlans in the indexer.
	// Objects returned here must be treated as read-only.
	List(selector labels.Selector) (ret []*v1alpha1.AuditPlan, err error)
	// AuditPlans returns an object that can list and get AuditPlans.
	AuditPlans(namespace string) AuditPlanNamespaceLister
	AuditPlanListerExpansion
}

// auditPlanLister implements the AuditPlanLister interface.
type auditPlanLister struct {
	indexer cache.Indexer
}

// NewAuditPlanLister returns a new AuditPlanLister.
func NewAuditPlanLister(indexer cache.Indexer) AuditPlanLister {
	return &auditPlanLister{indexer: indexer}
}

// List lists all AuditPlans in the indexer.
func (s *auditPlanLister) List(selector labels.Selector) (ret []*v1alpha1.AuditPlan, err error) {
	err = cache.ListAll(s.indexer, selector, func(m interface{}) {
		ret = append(ret, m.(*v1alpha1.AuditPlan))
	})
	return ret, err
}

// AuditPlans returns an object that can list and get AuditPlans.
func (s *auditPlanLister) AuditPlans(namespace string) AuditPlanNamespaceLister {
	return auditPlanNamespaceLister{indexer: s.indexer, namespace: namespace}
}

// AuditPlanNamespaceLister helps list and get AuditPlans.
// All objects returned here must be treated as read-only.
type AuditPlanNamespaceLister interface {
	// List lists all AuditPlans in the indexer for a given namespace.
	// Objects returned here must be treated as read-only.
	List(selector labels.Selector) (ret []*v1alpha1.AuditPlan, err error)
	// Get retrieves the AuditPlan from the indexer for a given namespace and name.
	// Objects returned here must be treated as read-only.
	Get(name string) (*v1alpha1.AuditPlan, error)
	AuditPlanNamespaceListerExpansion
}

// auditPlanNamespaceLister implements the AuditPlanNamespaceLister
// interface.
type auditPlanNamespaceLister struct {
	indexer   cache.Indexer
	namespace string
}

// List lists all AuditPlans in the indexer for a given namespace.
func (s auditPlanNamespaceLister) List(selector labels.Selector) (ret []*v1alpha1.AuditPlan, err error) {
	err = cache.ListAllByNamespace(s.indexer, s.namespace, selector, func(m interface{}) {
		ret = append(ret, m.(*v1alpha1.AuditPlan))
	})
	return ret, err
}

// Get retrieves the AuditPlan from the indexer for a given namespace and name.
func (s auditPlanNamespaceLister) Get(name string) (*v1alpha1.AuditPlan, error) {
	obj, exists, err := s.indexer.GetByKey(s.namespace + "/" + name)
	if err != nil {
		return nil, err
	}
	if !exists {
		return nil, errors.NewNotFound(v1alpha1.Resource("auditplan"), name)
	}
	return obj.(*v1alpha1.AuditPlan), nil
}
