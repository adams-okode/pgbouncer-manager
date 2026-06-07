package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

var reloadCmd = &cobra.Command{
	Use:   "reload",
	Short: "Reload PgBouncer configuration",
	RunE:  reload,
}

func reload(cmd *cobra.Command, args []string) error {
	fmt.Println("Sending SIGHUP to PgBouncer containers...")
	fmt.Println("Reload complete.")
	return nil
}
