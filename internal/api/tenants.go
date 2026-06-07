package api

import (
	"os"
	"strconv"
	"strings"

	"github.com/gofiber/fiber/v2"
	"predicta/pgbouncer-manager/internal/config"
	"predicta/pgbouncer-manager/internal/models"
	"predicta/pgbouncer-manager/internal/storage"
)

var configPath = os.Getenv("CONFIG_DIR")
var encryptionKey = os.Getenv("ENCRYPTION_KEY")

func getStorage() (*storage.CredentialStorage, error) {
	if encryptionKey == "" {
		encryptionKey = "default_key_12345678901234567890"
	}
	return storage.NewCredentialStorage(encryptionKey)
}

func addTenant(c *fiber.Ctx) error {
	tenant := new(models.Tenant)
	if err := c.BodyParser(tenant); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request body"})
	}

	if configPath == "" {
		configPath = "/root/Projects/Predicta/predicta-infra/pgbouncer/config"
	}

	cfg := config.NewConfig(
		configPath+"/pgbouncer-tx.ini",
		configPath+"/databases.ini",
		configPath+"/userlist.txt",
	)

	if err := cfg.Load(); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to load config"})
	}

	st, _ := getStorage()
	encryptedPass, _ := st.Encrypt(tenant.Password)

	cfg.Databases[tenant.ID] = tenant.getHostString() + " pool_size=" + strconv.Itoa(tenant.PoolSize)
	cfg.UserList[tenant.User] = encryptedPass

	if err := cfg.Save(); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to save config"})
	}

	return c.JSON(fiber.Map{"status": "success", "tenant": tenant})
}

func (t *models.Tenant) getHostString() string {
	return t.ID + " = host=" + t.Host + " port=" + strconv.Itoa(t.Port) +
		" dbname=" + t.DBName + " user=" + t.User
}

func listTenants(c *fiber.Ctx) error {
	if configPath == "" {
		configPath = "/root/Projects/Predicta/predicta-infra/pgbouncer/config"
	}

	cfg := config.NewConfig(
		configPath+"/pgbouncer-tx.ini",
		configPath+"/databases.ini",
		configPath+"/userlist.txt",
	)

	if err := cfg.Load(); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to load config"})
	}

	tenants := []models.TenantResponse{}
	for tenantID, dbConfig := range cfg.Databases {
		tenant := parseDBConfig(tenantID, dbConfig)
		tenants = append(tenants, tenant)
	}

	return c.JSON(fiber.Map{"tenants": tenants})
}

func parseDBConfig(id string, config string) models.TenantResponse {
	tenant := models.TenantResponse{ID: id}

	parts := map[string]string{}
	for _, part := range []string{"host", "port", "dbname", "user", "pool_size"} {
		for _, p := range strings.Split(config, " ") {
			if strings.HasPrefix(p, part+"=") {
				parts[part] = strings.Split(p, "=")[1]
			}
		}
	}

	tenant.Host = parts["host"]
	tenant.Port = 5432
	if parts["port"] != "" {
		tenant.Port, _ = strconv.Atoi(parts["port"])
	}
	tenant.DBName = parts["dbname"]
	tenant.User = parts["user"]
	tenant.PoolSize = 15
	if parts["pool_size"] != "" {
		tenant.PoolSize, _ = strconv.Atoi(parts["pool_size"])
	}

	return tenant
}

func getTenant(c *fiber.Ctx) error {
	id := c.Params("id")
	return c.JSON(fiber.Map{"error": "not implemented"})
}

func updateTenant(c *fiber.Ctx) error {
	id := c.Params("id")
	return c.JSON(fiber.Map{"error": "not implemented"})
}

func deleteTenant(c *fiber.Ctx) error {
	id := c.Params("id")
	return c.JSON(fiber.Map{"error": "not implemented"})
}

func rotateCredentials(c *fiber.Ctx) error {
	id := c.Params("id")
	return c.JSON(fiber.Map{"error": "not implemented"})
}

func setCredentials(c *fiber.Ctx) error {
	id := c.Params("id")
	return c.JSON(fiber.Map{"error": "not implemented"})
}
