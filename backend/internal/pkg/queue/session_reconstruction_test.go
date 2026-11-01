package queue

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestReconstructionRetriesPreserveFailedArtifacts(t *testing.T) {
	root := t.TempDir()
	original := filepath.Join(root, "result")
	if err := os.MkdirAll(original, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(original, "failure.json"), []byte("original failure"), 0600); err != nil {
		t.Fatal(err)
	}
	first, firstName, err := prepareReconstructionAttempt(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(first, "partial.ply"), []byte("partial geometry"), 0600); err != nil {
		t.Fatal(err)
	}
	second, secondName, err := prepareReconstructionAttempt(root)
	if err != nil {
		t.Fatal(err)
	}
	if first == second || firstName == secondName {
		t.Fatal("retry reused the failed attempt directory")
	}
	entries, err := os.ReadDir(second)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatal("new attempt is not empty")
	}
	for file, expected := range map[string]string{filepath.Join(original, "failure.json"): "original failure", filepath.Join(first, "partial.ply"): "partial geometry"} {
		data, err := os.ReadFile(file)
		if err != nil {
			t.Fatal(err)
		}
		if string(data) != expected {
			t.Fatal("previous artifacts changed")
		}
	}
	if filepath.Dir(second) != filepath.Join(root, "attempts", secondName) {
		t.Fatal("attempt is outside the job attempts directory")
	}
}

func TestQualityRejectionRequiresExplicitReport(t *testing.T) {
	root := t.TempDir()
	for _, data := range []string{"", "{", `{"final_verdict":"PASS","category_gates":{"MESH":false}}`} {
		if err := os.WriteFile(filepath.Join(root, "quality_gate.json"), []byte(data), 0600); err != nil {
			t.Fatal(err)
		}
		if got := reconstructionQualityRejection(root); got != "" {
			t.Fatalf("unexpected terminal failure: %s", got)
		}
	}
	os.WriteFile(filepath.Join(root, "quality_gate.json"), []byte(`{"final_verdict":"FAIL","category_gates":{"MESH":false,"DEPTH":true,"CAMERA":false}}`), 0600)
	os.WriteFile(filepath.Join(root, "mesh_validation.json"), []byte(`{"triangle_count":4608}`), 0600)
	got := reconstructionQualityRejection(root)
	if !strings.Contains(got, "CAMERA, MESH") || !strings.Contains(got, "triangles=4608") {
		t.Fatalf("missing reasons: %s", got)
	}
}
