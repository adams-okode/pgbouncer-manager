package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var tenantCmd = &cobra.Command{
	Use:   "tenant",
	Short: "Manage tenants",
}

var tenantAddCmd = &cobra.Command{
	Use:   "add --id=<id> --host=<host> --user=<user> --password=<pass>",
	Short: "Add a new tenant",
	RunE:  tenantAdd,
}

var tenantListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all tenants",
	RunE:  tenantList,
}

var tenantUpdateCmd = &cobra.Command{
	Use:   "update --id=<id> [--pool-size=<size>] [--password=<pass>]",
	Short: "Update tenant settings",
	RunE:  tenantUpdate,
}

var tenantRemoveCmd = &cobra.Command{
	Use:   "remove --id=<id>",
	Short: "Remove a tenant",
	RunE:  tenantRemove,
}

func init() {
	tenantAddCmd.Flags().String("id", "", "Tenant ID (required)")
	tenantAddCmd.Flags().String("host", "", "Database host (required)")
	tenantAddCmd.Flags().String("user", "postgres", "Database user")
	tenantAddCmd.Flags().String("password", "", "Database password (required)")
	tenantAddCmd.Flags().Int("pool-size", 15, "Pool size")

	tenantUpdateCmd.Flags().String("id", "", "Tenant ID (required)")
	tenantUpdateCmd.Flags().Int("pool-size", 0, "New pool size")
	tenantUpdateCmd.Flags().String("password", "", "New password")

	tenantRemoveCmd.Flags().String("id", "", "Tenant ID (required)")

	tenantCmd.AddCommand(tenantAddCmd)
	tenantCmd.AddCommand(tenantListCmd)
	tenantCmd.AddCommand(tenantUpdateCmd)
	tenantCmd.AddCommand(tenantRemoveCmd)
}

func tenantAdd(cmd *cobra.Command, args []string) error {
	id, _ := cmd.Flags().GetString("id")
	host, _ := cmd.Flags().GetString("host")
	user, _ := cmd.Flags().GetString("user")
	password, _ := cmd.Flags().GetString("password")
	poolSize, _ := cmd.Flags().GetInt("pool-size")

	if id == "" || host == "" || password == "" {
		return fmt.Errorf("--id, --host, and --password are required")
	}

	fmt.Printf("Adding tenant: %s @ %s\n", id, host)
	fmt.Printf("User: %s, Pool Size: %d\n", user, poolSize)

	return nil
}

func tenantList(cmd *cobra.Command, args []string) error {
	fmt.Println("Listing tenants...")
	return nil
}

func tenantUpdate(cmd *cobra.Command, args []string) error {
	id, _ := cmd.Flags().GetString("id")
	if id == "" {
		return fmt.Errorf("--id is required")
	}
	fmt.Printf("Updating tenant: %s\n", id)
	return nil
}

func tenantRemove(cmd *cobra.Command, args []string) error {
	id, _ := cmd.Flags().GetString("id")
	if id == "" {
		return fmt.Errorf("--id is required")
	}
	fmt.Printf("Removing tenant: %s\n", id)
	return nil
}
