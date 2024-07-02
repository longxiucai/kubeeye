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
// Code generated by client-gen. DO NOT EDIT.

package v1alpha2

import (
	"context"
	"time"

	v1alpha2 "github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"
	scheme "github.com/kubesphere/kubeeye/clients/clientset/versioned/scheme"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	types "k8s.io/apimachinery/pkg/types"
	watch "k8s.io/apimachinery/pkg/watch"
	rest "k8s.io/client-go/rest"
)

// InspectPlansGetter has a method to return a InspectPlanInterface.
// A group's client should implement this interface.
type InspectPlansGetter interface {
	InspectPlans() InspectPlanInterface
}

// InspectPlanInterface has methods to work with InspectPlan resources.
type InspectPlanInterface interface {
	Create(ctx context.Context, inspectPlan *v1alpha2.InspectPlan, opts v1.CreateOptions) (*v1alpha2.InspectPlan, error)
	Update(ctx context.Context, inspectPlan *v1alpha2.InspectPlan, opts v1.UpdateOptions) (*v1alpha2.InspectPlan, error)
	UpdateStatus(ctx context.Context, inspectPlan *v1alpha2.InspectPlan, opts v1.UpdateOptions) (*v1alpha2.InspectPlan, error)
	Delete(ctx context.Context, name string, opts v1.DeleteOptions) error
	DeleteCollection(ctx context.Context, opts v1.DeleteOptions, listOpts v1.ListOptions) error
	Get(ctx context.Context, name string, opts v1.GetOptions) (*v1alpha2.InspectPlan, error)
	List(ctx context.Context, opts v1.ListOptions) (*v1alpha2.InspectPlanList, error)
	Watch(ctx context.Context, opts v1.ListOptions) (watch.Interface, error)
	Patch(ctx context.Context, name string, pt types.PatchType, data []byte, opts v1.PatchOptions, subresources ...string) (result *v1alpha2.InspectPlan, err error)
	InspectPlanExpansion
}

// inspectPlans implements InspectPlanInterface
type inspectPlans struct {
	client rest.Interface
}

// newInspectPlans returns a InspectPlans
func newInspectPlans(c *KubeeyeV1alpha2Client) *inspectPlans {
	return &inspectPlans{
		client: c.RESTClient(),
	}
}

// Get takes name of the inspectPlan, and returns the corresponding inspectPlan object, and an error if there is any.
func (c *inspectPlans) Get(ctx context.Context, name string, options v1.GetOptions) (result *v1alpha2.InspectPlan, err error) {
	result = &v1alpha2.InspectPlan{}
	err = c.client.Get().
		Resource("inspectplans").
		Name(name).
		VersionedParams(&options, scheme.ParameterCodec).
		Do(ctx).
		Into(result)
	return
}

// List takes label and field selectors, and returns the list of InspectPlans that match those selectors.
func (c *inspectPlans) List(ctx context.Context, opts v1.ListOptions) (result *v1alpha2.InspectPlanList, err error) {
	var timeout time.Duration
	if opts.TimeoutSeconds != nil {
		timeout = time.Duration(*opts.TimeoutSeconds) * time.Second
	}
	result = &v1alpha2.InspectPlanList{}
	err = c.client.Get().
		Resource("inspectplans").
		VersionedParams(&opts, scheme.ParameterCodec).
		Timeout(timeout).
		Do(ctx).
		Into(result)
	return
}

// Watch returns a watch.Interface that watches the requested inspectPlans.
func (c *inspectPlans) Watch(ctx context.Context, opts v1.ListOptions) (watch.Interface, error) {
	var timeout time.Duration
	if opts.TimeoutSeconds != nil {
		timeout = time.Duration(*opts.TimeoutSeconds) * time.Second
	}
	opts.Watch = true
	return c.client.Get().
		Resource("inspectplans").
		VersionedParams(&opts, scheme.ParameterCodec).
		Timeout(timeout).
		Watch(ctx)
}

// Create takes the representation of a inspectPlan and creates it.  Returns the server's representation of the inspectPlan, and an error, if there is any.
func (c *inspectPlans) Create(ctx context.Context, inspectPlan *v1alpha2.InspectPlan, opts v1.CreateOptions) (result *v1alpha2.InspectPlan, err error) {
	result = &v1alpha2.InspectPlan{}
	err = c.client.Post().
		Resource("inspectplans").
		VersionedParams(&opts, scheme.ParameterCodec).
		Body(inspectPlan).
		Do(ctx).
		Into(result)
	return
}

// Update takes the representation of a inspectPlan and updates it. Returns the server's representation of the inspectPlan, and an error, if there is any.
func (c *inspectPlans) Update(ctx context.Context, inspectPlan *v1alpha2.InspectPlan, opts v1.UpdateOptions) (result *v1alpha2.InspectPlan, err error) {
	result = &v1alpha2.InspectPlan{}
	err = c.client.Put().
		Resource("inspectplans").
		Name(inspectPlan.Name).
		VersionedParams(&opts, scheme.ParameterCodec).
		Body(inspectPlan).
		Do(ctx).
		Into(result)
	return
}

// UpdateStatus was generated because the type contains a Status member.
// Add a +genclient:noStatus comment above the type to avoid generating UpdateStatus().
func (c *inspectPlans) UpdateStatus(ctx context.Context, inspectPlan *v1alpha2.InspectPlan, opts v1.UpdateOptions) (result *v1alpha2.InspectPlan, err error) {
	result = &v1alpha2.InspectPlan{}
	err = c.client.Put().
		Resource("inspectplans").
		Name(inspectPlan.Name).
		SubResource("status").
		VersionedParams(&opts, scheme.ParameterCodec).
		Body(inspectPlan).
		Do(ctx).
		Into(result)
	return
}

// Delete takes name of the inspectPlan and deletes it. Returns an error if one occurs.
func (c *inspectPlans) Delete(ctx context.Context, name string, opts v1.DeleteOptions) error {
	return c.client.Delete().
		Resource("inspectplans").
		Name(name).
		Body(&opts).
		Do(ctx).
		Error()
}

// DeleteCollection deletes a collection of objects.
func (c *inspectPlans) DeleteCollection(ctx context.Context, opts v1.DeleteOptions, listOpts v1.ListOptions) error {
	var timeout time.Duration
	if listOpts.TimeoutSeconds != nil {
		timeout = time.Duration(*listOpts.TimeoutSeconds) * time.Second
	}
	return c.client.Delete().
		Resource("inspectplans").
		VersionedParams(&listOpts, scheme.ParameterCodec).
		Timeout(timeout).
		Body(&opts).
		Do(ctx).
		Error()
}

// Patch applies the patch and returns the patched inspectPlan.
func (c *inspectPlans) Patch(ctx context.Context, name string, pt types.PatchType, data []byte, opts v1.PatchOptions, subresources ...string) (result *v1alpha2.InspectPlan, err error) {
	result = &v1alpha2.InspectPlan{}
	err = c.client.Patch(pt).
		Resource("inspectplans").
		Name(name).
		SubResource(subresources...).
		VersionedParams(&opts, scheme.ParameterCodec).
		Body(data).
		Do(ctx).
		Into(result)
	return
}
