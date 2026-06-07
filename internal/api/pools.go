package api

import (
	"strings"

	"github.com/gofiber/fiber/v2"
	"predicta/pgbouncer-manager/internal/models"
	"predicta/pgbouncer-manager/internal/pgbouncer"
)

func listPools(c *fiber.Ctx) error {
	client := pgbouncer.NewPgBouncerClient(true, "")

	poolLines, err := client.ShowPools()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}

	pools := []models.PoolStatus{}
	for _, line := range poolLines {
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 10 {
			continue
		}

		pool := models.PoolStatus{
			Database: fields[0],
			User:     fields[1],
			PoolMode: fields[2],
		}
	}

	return c.JSON(fiber.Map{"pools": pools})
}

func listStats(c *fiber.Ctx) error {
	client := pgbouncer.NewPgBouncerClient(true, "")

	statsLines, err := client.ShowStats()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}

	stats := []models.Stats{}
	for _, line := range statsLines {
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 20 {
			continue
		}

		stat := models.Stats{
			Database: fields[0],
			User:     fields[1],
			Type:     fields[2],
			State:    fields[3],
		}
		stats = append(stats, stat)
	}

	return c.JSON(fiber.Map{"stats": stats})
}

func reloadPgBouncer(c *fiber.Ctx) error {
	client := pgbouncer.NewPgBouncerClient(true, "")

	if err := client.Reload(); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}

	return c.JSON(fiber.Map{"status": "success", "message": "PgBouncer reloaded"})
}
