package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "pgbouncer-manager",
	Short: "PgBouncer Tenant Manager",
	Long:  "Manage PgBouncer tenants, pool sizes, and credentials via CLI or API",
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.AddCommand(tenantCmd)
	rootCmd.AddCommand(poolsCmd)
	rootCmd.AddCommand(reloadCmd)
}
