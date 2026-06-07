package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

var poolsCmd = &cobra.Command{
	Use:   "pools",
	Short: "Manage pools",
}

var poolsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List pool statistics",
	RunE:  poolsList,
}

func init() {
	poolsCmd.AddCommand(poolsListCmd)
}

func poolsList(cmd *cobra.Command, args []string) error {
	fmt.Println("Pool Statistics:")
	fmt.Println("Tenant       | Mode         | Active | Waiting | Idle")
	fmt.Println("-------------|--------------|--------|---------|------")
	return nil
}
