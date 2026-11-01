package queue

import (
	"bufio"
	"context"
	"encoding/json"
	"sort"

	"fmt"
	"github.com/hibiken/asynq"
	"io"
	"log"
	"mime"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/google/uuid"
	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/objectstore"
)

type SessionPipelineRecorder interface {
	RecordSessionStage(context.Context, string, uuid.UUID, string, string, *string) error
	PublishSessionViewer(context.Context, string, uuid.UUID, string) error
}

var pipelineStagePattern = regexp.MustCompile(`\[STAGE\s+(\d+)`)

func (h *StageHandlers) runSessionReconstruction(ctx context.Context, p *ReconstructionPayload) error {
	recorder, ok := h.jobRepo.(SessionPipelineRecorder)
	if !ok {
		return fmt.Errorf("session pipeline persistence unavailable")
	}
	if err := h.transition(ctx, p.JobID, domain.JobStagePreprocessing, 0); err != nil {
		return err
	}
	if err := recorder.RecordSessionStage(ctx, p.SessionID, p.JobID, "RECONSTRUCTION_00", "RUNNING", nil); err != nil {
		return err
	}
	output, attemptName, err := prepareReconstructionAttempt(p.WorkDir)
	if err != nil {
		return err
	}
	message := "Starting isolated reconstruction attempt: " + attemptName
	log.Printf("[CapturePipeline] session=%s job=%s %s", p.SessionID, p.JobID, message)
	_ = h.jobRepo.AddLog(ctx, &domain.JobLog{JobID: p.JobID, Stage: "RECONSTRUCTION_00", LogLevel: "info", Message: message})
	command := exec.CommandContext(ctx, "python3", "-u", "/app/scripts/capture_reconstruct.py", p.VideoURL, output)
	reader, writer := io.Pipe()
	command.Stdout = writer
	command.Stderr = writer
	if err := command.Start(); err != nil {
		reader.Close()
		writer.Close()
		return err
	}
	done := make(chan error, 1)
	go func() { err := command.Wait(); writer.Close(); done <- err }()
	current := "RECONSTRUCTION_00"
	scanner := bufio.NewScanner(reader)
	scanner.Buffer(make([]byte, 4096), 1<<20)
	for scanner.Scan() {
		line := scanner.Text()
		log.Printf("[CapturePipeline] session=%s job=%s %s", p.SessionID, p.JobID, line)
		_ = h.jobRepo.AddLog(ctx, &domain.JobLog{JobID: p.JobID, Stage: current, LogLevel: "info", Message: line})
		if match := pipelineStagePattern.FindStringSubmatch(line); len(match) > 1 {
			number, _ := strconv.Atoi(match[1])
			next := fmt.Sprintf("RECONSTRUCTION_%02d", number)
			if next != current {
				if err := recorder.RecordSessionStage(ctx, p.SessionID, p.JobID, current, "COMPLETED", nil); err != nil {
					command.Process.Kill()
					return err
				}
				current = next
				if err := recorder.RecordSessionStage(ctx, p.SessionID, p.JobID, current, "RUNNING", nil); err != nil {
					command.Process.Kill()
					return err
				}
			}
		}
	}
	reader.Close()
	if err := <-done; err != nil {
		if rejection := reconstructionQualityRejection(output); rejection != "" {
			_ = recorder.RecordSessionStage(ctx, p.SessionID, p.JobID, "QUALITY_VALIDATION", "FAILED", &rejection)
			_ = h.jobRepo.AddLog(ctx, &domain.JobLog{JobID: p.JobID, Stage: "QUALITY_VALIDATION", LogLevel: "error", Message: rejection})
			return fmt.Errorf("%s: %w", rejection, asynq.SkipRetry)
		}
		message := fmt.Sprintf("RECONSTRUCTION_FAILED: %v; inspect persisted job logs for the underlying error", err)
		_ = recorder.RecordSessionStage(ctx, p.SessionID, p.JobID, current, "RETRYING", &message)
		return fmt.Errorf("%s", message)
	}
	if err := scanner.Err(); err != nil {
		return err
	}
	if err := recorder.RecordSessionStage(ctx, p.SessionID, p.JobID, current, "COMPLETED", nil); err != nil {
		return err
	}
	if err := recorder.RecordSessionStage(ctx, p.SessionID, p.JobID, "VIEWER_PUBLISHING", "RUNNING", nil); err != nil {
		return err
	}
	store, err := objectstore.FromEnv()
	if err != nil {
		return err
	}
	// Publish generated files after quality validation. The local copy remains shared with the API.
	err = filepath.Walk(output, func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if info.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(output, path)
		if err != nil {
			return err
		}
		// Viewer and its direct assets are at the result root; intermediate data stays local.
		if strings.Contains(rel, string(filepath.Separator)) {
			return nil
		}
		kind := mime.TypeByExtension(filepath.Ext(path))
		if kind == "" {
			kind = "application/octet-stream"
		}
		return store.PutVerified(ctx, "vastu-artifacts", p.ProjectID.String()+"/"+p.JobID.String()+"/attempts/"+attemptName+"/"+filepath.ToSlash(rel), path, kind)
	})
	if err != nil {
		return err
	}
	viewerURL := "/uploads/scratch/" + p.JobID.String() + "/attempts/" + attemptName + "/result/index.html"
	if err := recorder.PublishSessionViewer(ctx, p.SessionID, p.JobID, viewerURL); err != nil {
		return err
	}
	return h.transition(ctx, p.JobID, domain.JobStageCompleted, 100)
}

// Each invocation, including Asynq retries, gets a fresh output directory. Failed
// artifacts remain available for diagnosis and can never be mistaken for new output.
func prepareReconstructionAttempt(workDir string) (string, string, error) {
	attempts := filepath.Join(workDir, "attempts")
	if err := os.MkdirAll(attempts, 0755); err != nil {
		return "", "", err
	}
	directory, err := os.MkdirTemp(attempts, "attempt-")
	if err != nil {
		return "", "", err
	}
	output := filepath.Join(directory, "result")
	if err := os.MkdirAll(output, 0755); err != nil {
		return "", "", err
	}
	return output, filepath.Base(directory), nil
}

// A measured quality rejection needs changed input or processing settings, not a transient retry.
// Only the current isolated attempt's explicit FAIL report is authoritative.
func reconstructionQualityRejection(output string) string {
	data, err := os.ReadFile(filepath.Join(output, "quality_gate.json"))
	if err != nil {
		return ""
	}
	var gate struct {
		Verdict string          `json:"final_verdict"`
		Gates   map[string]bool `json:"category_gates"`
	}
	if json.Unmarshal(data, &gate) != nil || gate.Verdict != "FAIL" {
		return ""
	}
	failed := []string{}
	for name, passed := range gate.Gates {
		if !passed {
			failed = append(failed, name)
		}
	}
	sort.Strings(failed)
	reason := strings.Join(failed, ", ")
	if reason == "" {
		reason = "unspecified quality check"
	}
	message := "RECONSTRUCTION_QUALITY_FAILED: " + reason + "; automatic retries stopped; inspect saved quality reports"
	if strings.Contains(reason, "MESH") {
		meshData, err := os.ReadFile(filepath.Join(output, "mesh_validation.json"))
		var mesh struct {
			Triangles int `json:"triangle_count"`
		}
		if err == nil && json.Unmarshal(meshData, &mesh) == nil {
			message += fmt.Sprintf("; mesh triangles=%d (final gate minimum=15000)", mesh.Triangles)
		}
	}
	return message
}
