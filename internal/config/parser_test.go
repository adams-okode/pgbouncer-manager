package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNewConfig(t *testing.T) {
	tmpDir := t.TempDir()
	cfg := NewConfig(
		filepath.Join(tmpDir, "pgbouncer.ini"),
		filepath.Join(tmpDir, "databases.ini"),
		filepath.Join(tmpDir, "userlist.txt"),
	)

	if cfg == nil {
		t.Fatal("expected config, got nil")
	}

	if cfg.IniPath == "" {
		t.Error("expected IniPath to be set")
	}
}

func TestLoadDatabases(t *testing.T) {
	tmpDir := t.TempDir()
	databasesFile := filepath.Join(tmpDir, "databases.ini")

	databasesContent := `tenant1 = host=localhost port=5432 dbname=test1 pool_size=15
tenant2 = host=localhost port=5432 dbname=test2 pool_size=20
; This is a comment
# This is also a comment
`
	if err := os.WriteFile(databasesFile, []byte(databasesContent), 0644); err != nil {
		t.Fatal(err)
	}

	cfg := NewConfig("", databasesFile, "")
	if err := cfg.Load(); err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(cfg.Databases) != 2 {
		t.Errorf("expected 2 databases, got %d", len(cfg.Databases))
	}

	if cfg.Databases["tenant1"] != "host=localhost port=5432 dbname=test1 pool_size=15" {
		t.Errorf("unexpected database config: %s", cfg.Databases["tenant1"])
	}
}

func TestLoadUserList(t *testing.T) {
	tmpDir := t.TempDir()
	userlistFile := filepath.Join(tmpDir, "userlist.txt")

	userlistContent := `"user1" "password1"
"user2" "password2"
# Comment
`
	if err := os.WriteFile(userlistFile, []byte(userlistContent), 0644); err != nil {
		t.Fatal(err)
	}

	cfg := NewConfig("", "", userlistFile)
	if err := cfg.Load(); err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(cfg.UserList) != 2 {
		t.Errorf("expected 2 users, got %d", len(cfg.UserList))
	}

	if cfg.UserList["user1"] != "password1" {
		t.Errorf("expected user1 password to be password1, got %s", cfg.UserList["user1"])
	}
}

func TestSaveDatabases(t *testing.T) {
	tmpDir := t.TempDir()
	databasesFile := filepath.Join(tmpDir, "databases.ini")

	cfg := NewConfig("", databasesFile, "")
	cfg.Databases["tenant1"] = "host=localhost port=5432 dbname=test1 pool_size=15"

	if err := cfg.Save(); err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	data, err := os.ReadFile(databasesFile)
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(data), "tenant1") {
		t.Error("expected tenant1 in databases.ini")
	}
}

func TestSaveUserList(t *testing.T) {
	tmpDir := t.TempDir()
	userlistFile := filepath.Join(tmpDir, "userlist.txt")

	cfg := NewConfig("", "", userlistFile)
	cfg.UserList["user1"] = "password1"

	if err := cfg.Save(); err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	data, err := os.ReadFile(userlistFile)
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(data), "user1") {
		t.Error("expected user1 in userlist.txt")
	}
}

func TestLoadEmptyFiles(t *testing.T) {
	tmpDir := t.TempDir()
	cfg := NewConfig(
		filepath.Join(tmpDir, "pgbouncer.ini"),
		filepath.Join(tmpDir, "databases.ini"),
		filepath.Join(tmpDir, "userlist.txt"),
	)

	if err := cfg.Load(); err != nil {
		t.Fatalf("expected no error for empty files, got %v", err)
	}

	if len(cfg.Databases) != 0 {
		t.Errorf("expected 0 databases, got %d", len(cfg.Databases))
	}

	if len(cfg.UserList) != 0 {
		t.Errorf("expected 0 users, got %d", len(cfg.UserList))
	}
}
