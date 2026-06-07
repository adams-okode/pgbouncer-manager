package api

import (
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
)

func NewServer() *fiber.App {
	app := fiber.New()

	app.Use(logger.New())
	app.Use(cors.New())

	app.Get("/", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"service": "pgbouncer-manager",
			"status":  "ok",
		})
	})

	app.Post("/tenants", addTenant)
	app.Get("/tenants", listTenants)
	app.Get("/tenants/:id", getTenant)
	app.Patch("/tenants/:id", updateTenant)
	app.Delete("/tenants/:id", deleteTenant)
	app.Post("/tenants/:id/rotate-credentials", rotateCredentials)
	app.Put("/tenants/:id/credentials", setCredentials)

	app.Get("/pools", listPools)
	app.Get("/stats", listStats)

	app.Post("/reload", reloadPgBouncer)

	return app
}
