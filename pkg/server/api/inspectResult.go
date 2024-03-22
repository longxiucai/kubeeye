package api

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"path"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"
	versionsv1alpha2 "github.com/kubesphere/kubeeye/clients/informers/externalversions/kubeeye/v1alpha2"
	"github.com/kubesphere/kubeeye/pkg/constant"
	"github.com/kubesphere/kubeeye/pkg/kube"
	"github.com/kubesphere/kubeeye/pkg/output"
	"github.com/kubesphere/kubeeye/pkg/server/query"
	"github.com/kubesphere/kubeeye/pkg/template"
	"github.com/kubesphere/kubeeye/pkg/utils"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/klog/v2"
)

type InspectResult struct {
	Clients *kube.KubernetesClient
	Ctx     context.Context
	Factory versionsv1alpha2.InspectResultInformer
}

func NewInspectResult(ctx context.Context, clients *kube.KubernetesClient, factory versionsv1alpha2.InspectResultInformer) *InspectResult {
	return &InspectResult{
		Clients: clients,
		Ctx:     ctx,
		Factory: factory,
	}
}

// ListInspectResult godoc
// @Summary      Show an Inspect
// @Description  get ListInspectResult
// @Tags         InspectResult
// @Accept       json
// @Produce      json
// @Param        sortBy query string false "sortBy=createTime"
// @Param        ascending query string false "ascending=true"
// @Param        limit query int false "limit=10"
// @Param        page query int false "page=1"
// @Param        labelSelector query string false "labelSelector=app=nginx"
// @Success      200 {array} v1alpha2.InspectResult
// @Router       /inspectresults [get]
func (i *InspectResult) ListInspectResult(gin *gin.Context) {
	q := query.ParseQuery(gin)
	parse, err := labels.Parse(q.LabelSelector)
	if err != nil {
		gin.JSON(http.StatusInternalServerError, err)
		return
	}
	ret, err := i.Factory.Lister().List(parse)
	if err != nil {
		gin.JSON(http.StatusInternalServerError, err)
		return
	}
	data := q.GetPageData(ret, i.compare, i.filter)
	outType, _ := gin.GetQuery("type")
	results := utils.MapToStruct[v1alpha2.InspectResult](data.Items.([]map[string]interface{})...)
	if outType == "customized" {
		var resultCustomized []map[string]interface{}
		for _, result := range results {
			d, e := i.GetFileResultData(result.Name)
			if e != nil {
				gin.JSON(http.StatusInternalServerError, NewErrors(e.Error(), "InspectResult"))
				return
			}

			resultCustomized = append(resultCustomized, output.ParseCustomizedStruct(d))

		}
		gin.JSON(http.StatusOK, resultCustomized)
		return
	} else if outType == "html" {
		var htmlContent strings.Builder
		htmlContent.WriteString("<html><body><ul>")
		for _, result := range results {
			htmlContent.WriteString("<li>")
			reqURL := gin.Request.URL.Path + "/" + result.Name + "?type=html"
			htmlContent.WriteString("<a href=\"")
			htmlContent.WriteString(reqURL)
			htmlContent.WriteString("\">")
			htmlContent.WriteString(result.Name)
			htmlContent.WriteString("</a>")
			htmlContent.WriteString("</li>")
		}
		htmlContent.WriteString("</ul></body></html>")
		gin.Data(http.StatusOK, "text/html; charset=utf-8", []byte(htmlContent.String()))
		return
	}

	details, _ := gin.GetQuery("details")
	if utils.StringToBool(details) {
		for k := range results {
			file, err := os.ReadFile(path.Join(constant.ResultPathPrefix, results[k].Name))
			if err != nil {
				gin.JSON(http.StatusInternalServerError, NewErrors(err.Error(), "InspectResult"))
				return
			}
			err = json.Unmarshal(file, &results[k])
			if err != nil {
				gin.JSON(http.StatusInternalServerError, NewErrors(err.Error(), "InspectResult"))
				return
			}
		}
	}
	gin.JSON(http.StatusOK, query.Result{
		TotalItems: data.TotalItems,
		Items:      results,
	})
}

// GetInspectResult godoc
// @Summary      Show an Inspect
// @Description  GetInspectResult
// @Tags         InspectResult
// @Accept       json
// @Produce      json
// @Param        name path string true "name"
// @Param        type query string false "type"
// @Success      200 {object} v1alpha2.InspectResult
// @Router       /inspectresults/{name} [get]
func (i *InspectResult) GetInspectResult(gin *gin.Context) {
	name := gin.Param("name")
	query.ParseQuery(gin)
	outType, _ := gin.GetQuery("type")
	switch outType {
	case "html":
		err, m := output.HtmlOut(name)
		if err != nil {
			gin.JSON(http.StatusInternalServerError, err)
			return
		}
		gin.HTML(http.StatusOK, template.InspectResultTemplate, m)
	case "customized":
		data, err := i.GetFileResultData(name)
		if err != nil {
			gin.JSON(http.StatusInternalServerError, NewErrors(err.Error(), "InspectResult"))
			return
		}
		customizedStruct := output.ParseCustomizedStruct(data)
		gin.JSON(http.StatusOK, customizedStruct)

	default:
		result, err := i.Factory.Lister().Get(name)
		if err != nil {
			klog.Error(err)
			gin.JSON(http.StatusInternalServerError, err)
			return
		}
		details, _ := gin.GetQuery("details")
		if utils.StringToBool(details) {
			file, err := os.ReadFile(path.Join(constant.ResultPathPrefix, result.Name))
			if err != nil {
				gin.JSON(http.StatusInternalServerError, NewErrors(err.Error(), "InspectResult"))
				return
			}
			err = json.Unmarshal(file, result)
			if err != nil {
				gin.JSON(http.StatusInternalServerError, NewErrors(err.Error(), "InspectResult"))
				return
			}
		}
		gin.JSON(http.StatusOK, result)
	}

}

func (i *InspectResult) compare(a, b map[string]interface{}, orderBy string) bool {
	left := utils.MapToStruct[v1alpha2.InspectResult](a)
	right := utils.MapToStruct[v1alpha2.InspectResult](b)

	switch orderBy {
	case query.CreateTime:
		return left[0].CreationTimestamp.Before(&right[0].CreationTimestamp)
	}
	return false
}

func (i *InspectResult) filter(data map[string]interface{}, f *query.Filter) bool {
	result := utils.MapToStruct[v1alpha2.InspectResult](data)[0]

	for k, v := range *f {
		switch k {
		case query.Name:
			return strings.Contains(result.Name, v)
		}
	}
	return false
}

func (i *InspectResult) GetFileResultData(name string) (*v1alpha2.InspectResult, error) {
	var results v1alpha2.InspectResult
	file, err := os.ReadFile(path.Join(constant.ResultPathPrefix, name))
	if err != nil {
		return nil, err
	}
	err = json.Unmarshal(file, &results)
	if err != nil {
		return nil, err
	}
	return &results, nil
}
