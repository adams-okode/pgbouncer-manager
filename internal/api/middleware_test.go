package api

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestBasicAuth(t *testing.T) {
	app := fiber.New()

	app.Use(BasicAuth("PgBouncer Manager"))
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	// Test without auth
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusUnauthorized {
		t.Errorf("expected 401, got %d", resp.StatusCode)
	}
}

func TestBasicAuth_InvalidCredentials(t *testing.T) {
	app := fiber.New()

	app.Use(BasicAuth("PgBouncer Manager"))
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	// Test with invalid credentials
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Basic dXNlcjpwYXNz") // user:pass base64
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if resp.StatusCode != http.StatusUnauthorized {
		t.Errorf("expected 401, got %d", resp.StatusCode)
	}
}

func TestBasicAuth_ValidCredentials(t *testing.T) {
	// This test is skipped as it requires a real userlist.txt
	t.Skip("skipping - requires userlist.txt")
}
