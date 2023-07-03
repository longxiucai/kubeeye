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

package v1alpha2

import (
	v1alpha2 "github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/tools/cache"
)

// InspectResultLister helps list InspectResults.
// All objects returned here must be treated as read-only.
type InspectResultLister interface {
	// List lists all InspectResults in the indexer.
	// Objects returned here must be treated as read-only.
	List(selector labels.Selector) (ret []*v1alpha2.InspectResult, err error)
	// InspectResults returns an object that can list and get InspectResults.
	InspectResults(namespace string) InspectResultNamespaceLister
	InspectResultListerExpansion
}

// inspectResultLister implements the InspectResultLister interface.
type inspectResultLister struct {
	indexer cache.Indexer
}

// NewInspectResultLister returns a new InspectResultLister.
func NewInspectResultLister(indexer cache.Indexer) InspectResultLister {
	return &inspectResultLister{indexer: indexer}
}

// List lists all InspectResults in the indexer.
func (s *inspectResultLister) List(selector labels.Selector) (ret []*v1alpha2.InspectResult, err error) {
	err = cache.ListAll(s.indexer, selector, func(m interface{}) {
		ret = append(ret, m.(*v1alpha2.InspectResult))
	})
	return ret, err
}

// InspectResults returns an object that can list and get InspectResults.
func (s *inspectResultLister) InspectResults(namespace string) InspectResultNamespaceLister {
	return inspectResultNamespaceLister{indexer: s.indexer, namespace: namespace}
}

// InspectResultNamespaceLister helps list and get InspectResults.
// All objects returned here must be treated as read-only.
type InspectResultNamespaceLister interface {
	// List lists all InspectResults in the indexer for a given namespace.
	// Objects returned here must be treated as read-only.
	List(selector labels.Selector) (ret []*v1alpha2.InspectResult, err error)
	// Get retrieves the InspectResult from the indexer for a given namespace and name.
	// Objects returned here must be treated as read-only.
	Get(name string) (*v1alpha2.InspectResult, error)
	InspectResultNamespaceListerExpansion
}

// inspectResultNamespaceLister implements the InspectResultNamespaceLister
// interface.
type inspectResultNamespaceLister struct {
	indexer   cache.Indexer
	namespace string
}

// List lists all InspectResults in the indexer for a given namespace.
func (s inspectResultNamespaceLister) List(selector labels.Selector) (ret []*v1alpha2.InspectResult, err error) {
	err = cache.ListAllByNamespace(s.indexer, s.namespace, selector, func(m interface{}) {
		ret = append(ret, m.(*v1alpha2.InspectResult))
	})
	return ret, err
}

// Get retrieves the InspectResult from the indexer for a given namespace and name.
func (s inspectResultNamespaceLister) Get(name string) (*v1alpha2.InspectResult, error) {
	obj, exists, err := s.indexer.GetByKey(s.namespace + "/" + name)
	if err != nil {
		return nil, err
	}
	if !exists {
		return nil, errors.NewNotFound(v1alpha2.Resource("inspectresult"), name)
	}
	return obj.(*v1alpha2.InspectResult), nil
}
