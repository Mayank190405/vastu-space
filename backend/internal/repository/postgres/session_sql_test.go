package postgres

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
)

// PostgreSQL resolves parameter types during PREPARE. Mock repository tests cannot
// detect SQLSTATE 42P08 when one parameter is used as both text and varchar.
// Run against a migrated database with TEST_DATABASE_URL. No rows are modified.
func TestPipelineStageParameterTypes(t *testing.T) {
	databaseURL := os.Getenv("TEST_DATABASE_URL")
	if databaseURL == "" {
		t.Skip("TEST_DATABASE_URL is required for SQL preparation regression tests")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	conn, err := pgx.Connect(ctx, databaseURL)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close(ctx)
	tx, err := conn.BeginTx(ctx, pgx.TxOptions{AccessMode: pgx.ReadOnly})
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback(ctx)
	for name, sql := range map[string]string{"capture_stage_update": updatePipelineStageSQL, "worker_stage_update": recordSessionStageSQL} {
		t.Run(name, func(t *testing.T) {
			if _, err := tx.Prepare(ctx, name, sql); err != nil {
				t.Fatal(err)
			}
		})
	}
}
