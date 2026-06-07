package api

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestListPools(t *testing.T) {
	app := NewServer()

	req := httptest.NewRequest(http.MethodGet, "/pools", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestListStats(t *testing.T) {
	app := NewServer()

	req := httptest.NewRequest(http.MethodGet, "/stats", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestReloadPgBouncer(t *testing.T) {
	app := NewServer()

	req := httptest.NewRequest(http.MethodPost, "/reload", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	// Should return 200 even if reload fails (graceful error handling)
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}
