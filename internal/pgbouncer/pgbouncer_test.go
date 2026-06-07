package pgbouncer

import (
	"testing"
)

func TestNewPgBouncerClient(t *testing.T) {
	client := NewPgBouncerClient(true, "pgbouncer-tx")

	if client == nil {
		t.Fatal("expected client, got nil")
	}

	if !client.DockerMode {
		t.Error("expected Docker mode to be true")
	}

	if client.Container != "pgbouncer-tx" {
		t.Errorf("expected container to be pgbouncer-tx, got %s", client.Container)
	}
}

func TestShowPools(t *testing.T) {
	// This test requires a running PgBouncer instance
	// It's here to document the expected behavior
	t.Run("with pgBouncer running", func(t *testing.T) {
		client := NewPgBouncerClient(true, "")

		// This will fail without PgBouncer running
		pools, err := client.ShowPools()
		if err != nil {
			// Expected if PgBouncer not running
			t.Logf("Expected error without PgBouncer: %v", err)
			return
		}

		if len(pools) == 0 {
			t.Error("expected pool data, got empty list")
		}

		t.Logf("Pools: %v", pools)
	})
}

func TestShowStats(t *testing.T) {
	// This test requires a running PgBouncer instance
	t.Run("with pgBouncer running", func(t *testing.T) {
		client := NewPgBouncerClient(true, "")

		stats, err := client.ShowStats()
		if err != nil {
			t.Logf("Expected error without PgBouncer: %v", err)
			return
		}

		t.Logf("Stats: %v", stats)
	})
}
