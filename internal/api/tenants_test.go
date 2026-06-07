package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gofiber/fiber/v2"
	"predicta/pgbouncer-manager/internal/models"
)

func TestAddTenant(t *testing.T) {
	app := fiber.New()

	app.Post("/tenants", addTenant)

	tenant := models.Tenant{
		ID:       "test1",
		Host:     "localhost",
		Port:     5432,
		DBName:   "testdb",
		User:     "testuser",
		Password: "testpass",
		PoolSize: 15,
	}

	body, _ := json.Marshal(tenant)

	req := httptest.NewRequest(http.MethodPost, "/tenants", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		t.Errorf("expected 200, got %d: %s", resp.StatusCode, string(body))
	}
}

func TestListTenants(t *testing.T) {
	app := fiber.New()

	app.Get("/tenants", listTenants)

	req := httptest.NewRequest(http.MethodGet, "/tenants", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	var result fiber.Map
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("expected valid JSON, got %v", err)
	}

	if _, ok := result["tenants"]; !ok {
		t.Error("expected 'tenants' key in response")
	}
}

func TestGetTenant(t *testing.T) {
	app := fiber.New()

	app.Get("/tenants/:id", getTenant)

	req := httptest.NewRequest(http.MethodGet, "/tenants/test1", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	// Should return 501 (not implemented) for now
	if resp.StatusCode != http.StatusNotImplemented {
		t.Errorf("expected 501, got %d", resp.StatusCode)
	}
}

func TestParseDBConfig(t *testing.T) {
	id := "tenant1"
	config := "host=localhost port=5432 dbname=testdb user=testuser pool_size=20"

	result := parseDBConfig(id, config)

	if result.ID != id {
		t.Errorf("expected ID %s, got %s", id, result.ID)
	}

	if result.Host != "localhost" {
		t.Errorf("expected host localhost, got %s", result.Host)
	}

	if result.Port != 5432 {
		t.Errorf("expected port 5432, got %d", result.Port)
	}

	if result.PoolSize != 20 {
		t.Errorf("expected pool_size 20, got %d", result.PoolSize)
	}
}

func TestParseDBConfig_Defaults(t *testing.T) {
	id := "tenant1"
	config := "host=localhost"

	result := parseDBConfig(id, config)

	if result.ID != id {
		t.Errorf("expected ID %s, got %s", id, result.ID)
	}

	if result.Port != 5432 {
		t.Errorf("expected default port 5432, got %d", result.Port)
	}

	if result.PoolSize != 15 {
		t.Errorf("expected default pool_size 15, got %d", result.PoolSize)
	}
}
