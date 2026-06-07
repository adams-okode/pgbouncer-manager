package api

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gofiber/fiber/v2"
)

func TestNewServer(t *testing.T) {
	app := NewServer()

	if app == nil {
		t.Fatal("expected app, got nil")
	}
}

func TestRootEndpoint(t *testing.T) {
	app := NewServer()

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}

	body := make(map[string]interface{})
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatalf("expected valid JSON, got %v", err)
	}

	if body["service"] != "pgbouncer-manager" {
		t.Errorf("expected service 'pgbouncer-manager', got %v", body["service"])
	}

	if body["status"] != "ok" {
		t.Errorf("expected status 'ok', got %v", body["status"])
	}
}

func TestRoutesExist(t *testing.T) {
	app := NewServer()

	routes := []struct {
		method string
		path   string
	}{
		{http.MethodPost, "/tenants"},
		{http.MethodGet, "/tenants"},
		{http.MethodGet, "/tenants/:id"},
		{http.MethodPatch, "/tenants/:id"},
		{http.MethodDelete, "/tenants/:id"},
		{http.MethodPost, "/tenants/:id/rotate-credentials"},
		{http.MethodPut, "/tenants/:id/credentials"},
		{http.MethodGet, "/pools"},
		{http.MethodGet, "/stats"},
		{http.MethodPost, "/reload"},
	}

	for _, route := range routes {
		req := httptest.NewRequest(route.method, route.path, nil)
		_, err := app.Test(req)
		if err != nil {
			t.Errorf("route %s %s failed: %v", route.method, route.path, err)
		}
	}
}
