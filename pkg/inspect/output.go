package inspect

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"text/tabwriter"

	"github.com/kubesphere/kubeeye/apis/kubeeye/v1alpha2"

	"github.com/pkg/errors"
)

func defaultOutput(receiver <-chan []v1alpha2.ResourceResult) error {
	w := tabwriter.NewWriter(os.Stdout, 10, 4, 3, ' ', 0)
	_, err := fmt.Fprintln(w, "\nNAMESPACE\tKIND\tNAME\tLEVEL\tMESSAGE\tREASON")
	if err != nil {
		return err
	}
	for r := range receiver {
		for _, results := range r {
			for _, items := range results.ResultItems {
				s := fmt.Sprintf("%s\t%s\t%s\t%s\t%s\t%-8v", results.NameSpace, results.ResourceType,
					results.Name, items.Level, items.Message, items.Reason)
				_, err := fmt.Fprintln(w, s)
				if err != nil {
					return err
				}
			}
		}
	}
	if err := w.Flush(); err != nil {
		return err
	}
	return nil
}

func JSONOutput(receiver <-chan []v1alpha2.ResourceResult) error {
	var output []v1alpha2.ResourceResult
	for r := range receiver {
		for _, results := range r {
			output = append(output, results)
		}
	}

	// output json
	jsonOutput, err := json.MarshalIndent(output, "", "    ")
	if err != nil {
		return err
	}
	fmt.Println(string(jsonOutput))
	return nil
}

func CSVOutput(receiver <-chan []v1alpha2.ResourceResult) error {
	filename := "kubeEyeAuditResult.csv"
	// create csv file
	newFile, err := os.Create(filename)
	if err != nil {
		return errors.Wrap(err, "create file kubeEyeAuditResult.csv failed.")
	}

	defer newFile.Close()

	// write UTF-8 BOM to prevent print gibberish.
	if _, err = newFile.WriteString("\xEF\xBB\xBF"); err != nil {
		return err
	}

	// NewWriter returns a new Writer that writes to w.
	w := csv.NewWriter(newFile)
	header := []string{"namespace", "kind", "name", "level", "message", "reason"}
	contents := [][]string{
		header,
	}
	for r := range receiver {
		for _, results := range r {
			var resourceName string
			for _, items := range results.ResultItems {
				if resourceName == "" {
					content := []string{
						results.NameSpace,
						results.ResourceType,
						results.Name,
						items.Level,
						items.Message,
						items.Reason,
					}
					contents = append(contents, content)
					resourceName = results.Name
				} else {
					content := []string{
						"",
						"",
						"",
						items.Level,
						items.Message,
						items.Reason,
					}
					contents = append(contents, content)
				}

			}
		}
	}
	// WriteAll writes multiple CSV records to w using Write and then calls Flush,
	if err := w.WriteAll(contents); err != nil {
		return err
	}
	fmt.Printf("The result is exported to kubeEyeAuditResult.CSV, please check it for inspect result.\n")
	return nil
}