package main

import (
	"log"
	"os"

	"predicta/pgbouncer-manager/internal/api"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "3000"
	}

	app := api.NewServer()

	log.Printf("Starting PgBouncer Manager on port %s", port)
	if err := app.Listen(":" + port); err != nil {
		log.Fatal(err)
	}
}
