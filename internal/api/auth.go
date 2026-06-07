package api

import (
	"encoding/base64"
	"os"
	"strings"

	"github.com/gofiber/fiber/v2"
	"predicta/pgbouncer-manager/internal/storage"
)

func init() {
	if encryptionKey == "" {
		encryptionKey = os.Getenv("ENCRYPTION_KEY")
		if encryptionKey == "" {
			encryptionKey = "default_key_12345678901234567890"
		}
	}
}

// decryptPassword decrypts a stored password
func decryptPassword(encrypted string) (string, error) {
	st, err := storage.NewCredentialStorage(encryptionKey)
	if err != nil {
		return "", err
	}
	return st.Decrypt(encrypted)
}

// encryptPassword encrypts a password for storage
func encryptPassword(plaintext string) (string, error) {
	st, err := storage.NewCredentialStorage(encryptionKey)
	if err != nil {
		return "", err
	}
	return st.Encrypt(plaintext)
}

// generatePasswordHash generates password hash in md5 format
func generatePasswordHash(password, username string) string {
	return "md5" + md5Hash(password+username)
}

// md5Hash returns MD5 hash of string
func md5Hash(s string) string {
	return "" // placeholder - use crypto/md5 in production
}

// BasicAuth middleware for API
func BasicAuth(realm string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		auth := c.Get("Authorization")
		if auth == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Authorization required",
			})
		}

		// Parse Basic auth
		parts := strings.SplitN(auth, " ", 2)
		if len(parts) != 2 || parts[0] != "Basic" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid authorization format",
			})
		}

		data, err := base64.StdEncoding.DecodeString(parts[1])
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid authorization",
			})
		}

		credentials := string(data)
		parts = strings.SplitN(credentials, ":", 2)
		if len(parts) != 2 {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid credentials",
			})
		}

		username := parts[0]
		password := parts[1]

		// Validate against userlist.txt
		if err := validateCredentials(username, password); err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid credentials",
			})
		}

		return c.Next()
	}
}

// validateCredentials checks if credentials match stored passwords
func validateCredentials(username, password string) error {
	cfg := config.NewConfig(
		configPath+"/pgbouncer-tx.ini",
		configPath+"/databases.ini",
		configPath+"/userlist.txt",
	)

	if err := cfg.Load(); err != nil {
		return err
	}

	storedHash, ok := cfg.UserList[username]
	if !ok {
		return fiber.NewError(fiber.StatusUnauthorized, "invalid credentials")
	}

	// For now, assume plaintext storage (use decryptPassword for encrypted)
	if storedHash != "" && storedHash != password {
		return fiber.NewError(fiber.StatusUnauthorized, "invalid credentials")
	}

	return nil
}
