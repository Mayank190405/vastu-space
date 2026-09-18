package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/handler"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type mockJobRepo struct {
	jobs map[uuid.UUID]*domain.ProcessingJob
	logs map[uuid.UUID][]*domain.JobLog
}

func newMockJobRepo() *mockJobRepo {
	return &mockJobRepo{
		jobs: make(map[uuid.UUID]*domain.ProcessingJob),
		logs: make(map[uuid.UUID][]*domain.JobLog),
	}
}

func (m *mockJobRepo) Create(ctx context.Context, job *domain.ProcessingJob) error {
	m.jobs[job.ID] = job
	return nil
}

func (m *mockJobRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.ProcessingJob, error) {
	j, ok := m.jobs[id]
	if !ok {
		return nil, domain.ErrJobNotFound
	}
	return j, nil
}

func (m *mockJobRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ProcessingJob, error) {
	var list []*domain.ProcessingJob
	for _, j := range m.jobs {
		if j.ProjectID == projectID {
			list = append(list, j)
		}
	}
	return list, nil
}

func (m *mockJobRepo) UpdateProgress(ctx context.Context, id uuid.UUID, stage domain.JobStage, progress int, workerNodeID, errorCode, errorMessage *string) error {
	j, ok := m.jobs[id]
	if !ok {
		return domain.ErrJobNotFound
	}
	j.Stage = stage
	j.ProgressPercentage = progress
	if workerNodeID != nil {
		j.WorkerNodeID = workerNodeID
	}
	if errorCode != nil {
		j.ErrorCode = errorCode
	}
	if errorMessage != nil {
		j.ErrorMessage = errorMessage
	}
	j.UpdatedAt = time.Now().UTC()
	return nil
}

func (m *mockJobRepo) AddLog(ctx context.Context, log *domain.JobLog) error {
	m.logs[log.JobID] = append(m.logs[log.JobID], log)
	return nil
}

func (m *mockJobRepo) ListLogs(ctx context.Context, jobID uuid.UUID) ([]*domain.JobLog, error) {
	return m.logs[jobID], nil
}

func setupJobRouter() (*chi.Mux, *mockJobRepo) {
	jobRepo := newMockJobRepo()
	jobSvc := service.NewJobService(jobRepo, nil, nil)
	jobHdl := handler.NewJobHandler(jobSvc)

	r := chi.NewRouter()
	r.Post("/api/v1/jobs", jobHdl.Create)
	r.Get("/api/v1/jobs/{id}", jobHdl.Get)
	r.Get("/api/v1/projects/{projectId}/jobs", jobHdl.ListByProject)
	r.Post("/api/v1/jobs/{id}/progress", jobHdl.UpdateProgress)
	r.Post("/api/v1/jobs/{id}/logs", jobHdl.AddLog)
	r.Get("/api/v1/jobs/{id}/logs", jobHdl.GetLogs)

	return r, jobRepo
}

func TestJobAPI(t *testing.T) {
	router, jobRepo := setupJobRouter()
	projectID := uuid.New()
	captureID := uuid.New()

	var jobID uuid.UUID

	t.Run("POST /api/v1/jobs - Create Reconstruction Job", func(t *testing.T) {
		prio := 8
		input := domain.CreateJobInput{
			ProjectID: projectID,
			CaptureID: &captureID,
			Priority:  &prio,
		}
		data, _ := json.Marshal(input)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/jobs", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusCreated, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		dataMap := resp["data"].(map[string]interface{})
		parsedID, err := uuid.Parse(dataMap["id"].(string))
		require.NoError(t, err)
		jobID = parsedID

		assert.Equal(t, string(domain.JobStageQueued), dataMap["stage"])
		assert.Equal(t, float64(8), dataMap["priority"])
	})

	t.Run("GET /api/v1/jobs/{id} - Get Job Details", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/jobs/"+jobID.String(), nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		dataMap := resp["data"].(map[string]interface{})
		assert.Equal(t, jobID.String(), dataMap["id"])
	})

	t.Run("GET /api/v1/projects/{projectId}/jobs - List Jobs By Project", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/projects/"+projectID.String()+"/jobs", nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		dataList := resp["data"].([]interface{})
		assert.Len(t, dataList, 1)
	})

	t.Run("POST /api/v1/jobs/{id}/progress - Update Job Stage and Progress", func(t *testing.T) {
		workerNode := "worker-gpu-01"
		progressInput := domain.UpdateJobProgressInput{
			Stage:              domain.JobStageMeshing,
			ProgressPercentage: 65,
			WorkerNodeID:       &workerNode,
		}
		data, _ := json.Marshal(progressInput)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/jobs/"+jobID.String()+"/progress", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		// Verify in repo
		job, _ := jobRepo.GetByID(context.Background(), jobID)
		assert.Equal(t, domain.JobStageMeshing, job.Stage)
		assert.Equal(t, 65, job.ProgressPercentage)
	})

	t.Run("POST /api/v1/jobs/{id}/logs - Append Worker Log", func(t *testing.T) {
		logInput := map[string]interface{}{
			"stage":   string(domain.JobStageMeshing),
			"level":   "info",
			"message": "Poisson surface reconstruction completed with 450,000 faces",
		}
		data, _ := json.Marshal(logInput)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/jobs/"+jobID.String()+"/logs", bytes.NewReader(data))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)
	})

	t.Run("GET /api/v1/jobs/{id}/logs - Retrieve Job Logs", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/jobs/"+jobID.String()+"/logs", nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		logsList := resp["data"].([]interface{})
		assert.GreaterOrEqual(t, len(logsList), 2) // initial log + meshing log
	})
}
