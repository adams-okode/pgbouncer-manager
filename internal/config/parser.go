package config

import (
	"fmt"
	"os"
	"strings"

	"gopkg.in/ini.v1"
)

type PgBouncerConfig struct {
	IniPath       string
	DatabasesPath string
	UserListPath  string
	Databases     map[string]string
	UserList      map[string]string
}

func NewConfig(iniPath, databasesPath, userlistPath string) *PgBouncerConfig {
	return &PgBouncerConfig{
		IniPath:       iniPath,
		DatabasesPath: databasesPath,
		UserListPath:  userlistPath,
		Databases:     make(map[string]string),
		UserList:      make(map[string]string),
	}
}

func (c *PgBouncerConfig) Load() error {
	if err := c.loadDatabases(); err != nil {
		return err
	}
	if err := c.loadUserList(); err != nil {
		return err
	}
	return nil
}

func (c *PgBouncerConfig) loadDatabases() error {
	data, err := os.ReadFile(c.DatabasesPath)
	if err != nil {
		return fmt.Errorf("reading databases.ini: %w", err)
	}

	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, ";") || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			tenantID := strings.TrimSpace(parts[0])
			config := strings.TrimSpace(parts[1])
			c.Databases[tenantID] = config
		}
	}

	return nil
}

func (c *PgBouncerConfig) loadUserList() error {
	data, err := os.ReadFile(c.UserListPath)
	if err != nil {
		return fmt.Errorf("reading userlist.txt: %w", err)
	}

	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, ";") || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.SplitN(line, " ", 2)
		if len(parts) == 2 {
			user := strings.Trim(parts[0], "\"")
			pass := strings.Trim(parts[1], "\"")
			c.UserList[user] = pass
		}
	}

	return nil
}

func (c *PgBouncerConfig) Save() error {
	if err := c.saveDatabases(); err != nil {
		return err
	}
	if err := c.saveUserList(); err != nil {
		return err
	}
	return nil
}

func (c *PgBouncerConfig) saveDatabases() error {
	file, err := ini.Load([]byte{})
	if err != nil {
		return err
	}

	file.CommentByte = ';'
	file.Comment = ";"

	for tenantID, config := range c.Databases {
		section, err := file.NewSection(tenantID)
		if err != nil {
			return err
		}
		section.Comment = ""
		section.Key("", config)
	}

	return file.SaveTo(c.DatabasesPath)
}

func (c *PgBouncerConfig) saveUserList() error {
	lines := []string{"# userlist.txt"}
	for user, pass := range c.UserList {
		lines = append(lines, fmt.Sprintf(`"%s" "%s"`, user, pass))
	}

	return os.WriteFile(c.UserListPath, []byte(strings.Join(lines, "\n")+"\n"), 0644)
}

// GeneratePgBouncerINI generates a pgbouncer.ini file content
func (c *PgBouncerConfig) GeneratePgBouncerINI(poolMode string, maxConn int, poolSize int, reserveSize int) string {
	return `; PgBouncer configuration
%include /etc/pgbouncer/databases.ini

[pgbouncer]
listen_port = 6432
listen_addr = *
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

pool_mode = ` + poolMode + `
max_client_conn = ` + fmt.Sprintf("%d", maxConn) + `
default_pool_size = ` + fmt.Sprintf("%d", poolSize) + `
min_pool_size = 5
reserve_pool_size = ` + fmt.Sprintf("%d", reserveSize) + `
reserve_pool_timeout = 3

server_tls_sslmode = require

; SQLAlchemy sends these on connect — suppress the warnings
ignore_startup_parameters = extra_float_digits,search_path

log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
stats_period = 60

admin_users = pgbouncer
`
}
