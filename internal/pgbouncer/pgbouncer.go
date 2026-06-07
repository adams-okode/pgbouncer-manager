package pgbouncer

import (
	"bytes"
	"fmt"
	"os/exec"
	"strings"
)

type PgBouncerClient struct {
	DockerMode bool
	Container  string
}

func NewPgBouncerClient(dockerMode bool, container string) *PgBouncerClient {
	return &PgBouncerClient{
		DockerMode: dockerMode,
		Container:  container,
	}
}

func (c *PgBouncerClient) Reload() error {
	if c.DockerMode {
		return c.reloadDocker()
	}
	return c.reloadDirect()
}

func (c *PgBouncerClient) reloadDocker() error {
	cmd := exec.Command("docker", "kill", "--signal=HUP", "pgbouncer-tx", "pgbouncer-session")
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("docker kill failed: %w, stderr: %s", err, stderr.String())
	}

	return nil
}

func (c *PgBouncerClient) reloadDirect() error {
	cmd := exec.Command("psql", "-h", "localhost", "-p", "6543", "-U", "pgbouncer", "-d", "pgbouncer", "-c", "RELOAD;")
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("psql reload failed: %w, stderr: %s", err, stderr.String())
	}

	return nil
}

func (c *PgBouncerClient) ShowPools() ([]string, error) {
	cmd := exec.Command("psql", "-h", "localhost", "-p", "6543", "-U", "pgbouncer", "-d", "pgbouncer", "-c", "SHOW POOLS;")
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("SHOW POOLS failed: %w, stderr: %s", err, stderr.String())
	}

	output := strings.TrimSpace(stdout.String())
	lines := strings.Split(output, "\n")

	if len(lines) > 1 {
		return lines[1:], nil
	}

	return nil, nil
}

func (c *PgBouncerClient) ShowStats() ([]string, error) {
	cmd := exec.Command("psql", "-h", "localhost", "-p", "6543", "-U", "pgbouncer", "-d", "pgbouncer", "-c", "SHOW STATS;")
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("SHOW STATS failed: %w, stderr: %s", err, stderr.String())
	}

	output := strings.TrimSpace(stdout.String())
	lines := strings.Split(output, "\n")

	if len(lines) > 1 {
		return lines[1:], nil
	}

	return nil, nil
}
