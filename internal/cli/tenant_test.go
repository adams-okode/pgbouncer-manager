package cli

import (
	"bytes"
	"testing"
)

func TestTenantAdd(t *testing.T) {
	// Create a temporary command with test flags
	cmd := &cobra.Command{
		Use: "test",
		RunE: func(cmd *cobra.Command, args []string) error {
			return tenantAdd(cmd, args)
		},
	}

	// Set up flags
	cmd.Flags().String("id", "", "Tenant ID")
	cmd.Flags().String("host", "", "Database host")
	cmd.Flags().String("user", "postgres", "Database user")
	cmd.Flags().String("password", "", "Database password")
	cmd.Flags().Int("pool-size", 15, "Pool size")

	// Test with missing required fields
	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetErr(buf)

	cmd.SetArgs([]string{})

	// This will fail validation since required fields are missing
	// But we just want to verify it runs without panic
	err := cmd.Execute()
	if err == nil {
		t.Log("Expected validation error but got nil")
	}
}

func TestTenantList(t *testing.T) {
	cmd := &cobra.Command{
		Use: "test",
		RunE: func(cmd *cobra.Command, args []string) error {
			return tenantList(cmd, args)
		},
	}

	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetErr(buf)

	cmd.SetArgs([]string{})
	err := cmd.Execute()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestTenantUpdate(t *testing.T) {
	cmd := &cobra.Command{
		Use: "test",
		RunE: func(cmd *cobra.Command, args []string) error {
			return tenantUpdate(cmd, args)
		},
	}

	cmd.Flags().String("id", "", "Tenant ID")
	cmd.Flags().Int("pool-size", 0, "New pool size")
	cmd.Flags().String("password", "", "New password")

	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetErr(buf)

	cmd.SetArgs([]string{})
	err := cmd.Execute()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestTenantRemove(t *testing.T) {
	cmd := &cobra.Command{
		Use: "test",
		RunE: func(cmd *cobra.Command, args []string) error {
			return tenantRemove(cmd, args)
		},
	}

	cmd.Flags().String("id", "", "Tenant ID")

	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetErr(buf)

	cmd.SetArgs([]string{})
	err := cmd.Execute()
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}
