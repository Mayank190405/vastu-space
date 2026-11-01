package handler

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"vastu/backend/internal/domain"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/pkg/objectstore"
	"vastu/backend/internal/repository"
	"vastu/backend/internal/repository/postgres"
	"vastu/backend/internal/service"
)

type MobileUploadHandler struct {
	pool          *pgxpool.Pool
	sessions      *postgres.SessionRepository
	captures      repository.CaptureRepository
	uploads       repository.UploadRepository
	uploadService *service.UploadService
	jobs          *service.JobService
	stages        *service.SessionManagerService
	uploadDir     string
}

func NewMobileUploadHandler(pool *pgxpool.Pool, sessions *postgres.SessionRepository, captures repository.CaptureRepository, uploads repository.UploadRepository, uploadService *service.UploadService, jobs *service.JobService, stages *service.SessionManagerService, dir string) *MobileUploadHandler {
	return &MobileUploadHandler{pool, sessions, captures, uploads, uploadService, jobs, stages, dir}
}
func (h *MobileUploadHandler) lock(ctx context.Context, id string) (pgx.Tx, error) {
	tx, err := h.pool.Begin(ctx)
	if err != nil {
		return nil, err
	}
	_, err = tx.Exec(ctx, "SELECT pg_advisory_xact_lock(hashtext($1))", id)
	if err != nil {
		tx.Rollback(ctx)
		return nil, err
	}
	return tx, nil
}
func (h *MobileUploadHandler) Init(w http.ResponseWriter, r *http.Request) {
	sid := chi.URLParam(r, "sessionId")
	tx, err := h.lock(r.Context(), sid)
	if err != nil {
		JSONError(w, 503, "SESSION_BUSY")
		return
	}
	defer tx.Rollback(r.Context())
	session, err := h.sessions.GetSessionByID(r.Context(), sid)
	if err != nil {
		JSONError(w, 404, "SESSION_NOT_FOUND")
		return
	}
	var input domain.InitUploadInput
	if json.NewDecoder(http.MaxBytesReader(w, r.Body, 64<<10)).Decode(&input) != nil || input.TotalSizeBytes <= 0 || input.TotalSizeBytes > 5*1024*1024*1024 || input.SHA256Checksum == nil || len(*input.SHA256Checksum) != 64 {
		JSONError(w, 400, "VIDEO_SIZE_AND_SHA256_REQUIRED")
		return
	}
	if session.UploadID != nil {
		upload, err := h.uploads.GetSessionByID(r.Context(), *session.UploadID)
		if err != nil {
			JSONError(w, 503, "UPLOAD_LOOKUP_FAILED")
			return
		}
		if upload.TotalSizeBytes != input.TotalSizeBytes || upload.SHA256Checksum == nil || *upload.SHA256Checksum != *input.SHA256Checksum {
			JSONError(w, 409, "SESSION_ALREADY_BOUND_TO_DIFFERENT_VIDEO")
			return
		}
		JSONSuccess(w, 200, "Resume existing video upload", upload)
		return
	}
	captureID := uuid.NewSHA1(uuid.NameSpaceURL, []byte("vastu:capture:"+sid))
	if _, err = h.captures.GetByID(r.Context(), captureID); err != nil {
		device := "Mobile device"
		if session.DeviceID != nil {
			device = *session.DeviceID
		}
		capture := &domain.Capture{ID: captureID, ProjectID: session.ProjectID, SectionID: session.RoomID, DeviceModel: device, DeviceOS: "iOS", CaptureMode: domain.CaptureModeRGBIMU, Status: domain.CaptureStatusRecording, FileSizeBytes: input.TotalSizeBytes}
		if err = h.captures.Create(r.Context(), capture); err != nil {
			JSONError(w, 503, "CAPTURE_CREATE_FAILED: "+err.Error())
			return
		}
	}
	input.CaptureID = &captureID
	input.FileName = "capture.mp4"
	input.FileType = "video"
	input.ChunkSizeBytes = 2 << 20
	input.TotalChunks = 0
	upload, err := h.uploadService.InitSession(r.Context(), uuid.Nil, input)
	if err != nil {
		JSONError(w, 400, err.Error())
		return
	}
	_, err = tx.Exec(r.Context(), "UPDATE capture_sessions SET capture_id=$2,upload_id=$3,status='UPLOADING',updated_at=NOW() WHERE id=$1", sid, captureID, upload.ID)
	if err == nil {
		err = tx.Commit(r.Context())
	}
	if err != nil {
		JSONError(w, 503, "UPLOAD_BIND_FAILED")
		return
	}
	_, _ = h.stages.UpdateStage(r.Context(), sid, "UPLOADING", domain.UpdatePipelineStageInput{Status: domain.StageStatusRunning})
	JSONSuccess(w, 201, "Video upload initialized", upload)
}
func (h *MobileUploadHandler) uploadID(r *http.Request) (uuid.UUID, error) {
	s, err := h.sessions.GetSessionByID(r.Context(), chi.URLParam(r, "sessionId"))
	if err != nil {
		return uuid.Nil, err
	}
	if s.UploadID == nil {
		return uuid.Nil, errors.New("UPLOAD_NOT_INITIALIZED")
	}
	return *s.UploadID, nil
}
func (h *MobileUploadHandler) Chunk(w http.ResponseWriter, r *http.Request) {
	id, err := h.uploadID(r)
	if err != nil {
		JSONError(w, 409, err.Error())
		return
	}
	index, err := strconv.Atoi(chi.URLParam(r, "chunkIndex"))
	if err != nil {
		JSONError(w, 400, "INVALID_CHUNK_INDEX")
		return
	}
	tx, err := h.lock(r.Context(), id.String()+":"+strconv.Itoa(index))
	if err != nil {
		JSONError(w, 503, "CHUNK_BUSY")
		return
	}
	defer tx.Rollback(r.Context())
	chunk, err := h.uploadService.SaveChunk(r.Context(), id, index, r.Header.Get("X-Chunk-SHA256"), http.MaxBytesReader(w, r.Body, (2<<20)+1))
	if err != nil {
		JSONError(w, 400, err.Error())
		return
	}
	JSONSuccess(w, 200, "Chunk stored", chunk)
}
func (h *MobileUploadHandler) Progress(w http.ResponseWriter, r *http.Request) {
	id, err := h.uploadID(r)
	if err != nil {
		JSONError(w, 409, err.Error())
		return
	}
	progress, err := h.uploadService.GetProgress(r.Context(), id)
	if err != nil {
		JSONError(w, 503, err.Error())
		return
	}
	JSONSuccess(w, 200, "Upload progress", progress)
}
func (h *MobileUploadHandler) Complete(w http.ResponseWriter, r *http.Request) {
	sid := chi.URLParam(r, "sessionId")
	tx, err := h.lock(r.Context(), sid)
	if err != nil {
		JSONError(w, 503, "SESSION_BUSY")
		return
	}
	defer tx.Rollback(r.Context())
	session, err := h.sessions.GetSessionByID(r.Context(), sid)
	if err != nil || session.UploadID == nil || session.CaptureID == nil {
		JSONError(w, 409, "UPLOAD_NOT_INITIALIZED")
		return
	}
	if session.JobID != nil {
		job, err := h.jobs.GetJob(r.Context(), *session.JobID)
		if err != nil {
			JSONError(w, 503, "JOB_LOOKUP_FAILED")
			return
		}
		if job.Stage == domain.JobStageFailed {
			JSONError(w, 409, "PROCESSING_FAILED: "+fmt.Sprint(job.ErrorMessage))
			return
		}
		JSONSuccess(w, 200, "Upload verified and processing submitted", session)
		return
	}
	store, err := objectstore.FromEnv()
	if err != nil {
		JSONError(w, 503, "STORAGE_NOT_CONFIGURED")
		return
	}
	videoURL, err := h.uploadService.CompleteUpload(r.Context(), *session.UploadID, "")
	if err != nil {
		JSONError(w, 409, "UPLOAD_VERIFICATION_FAILED: "+err.Error())
		return
	}
	path := filepath.Join(h.uploadDir, "clean", filepath.Base(videoURL))
	if _, err = os.Stat(path); err != nil {
		JSONError(w, 409, "VIDEO_MISSING")
		return
	}
	key := session.ProjectID.String() + "/" + sid + "/capture.mp4"
	if err = store.PutVerified(r.Context(), store.RawBucket, key, path, "video/mp4"); err != nil {
		JSONError(w, 503, "S3_VERIFICATION_FAILED: "+err.Error())
		return
	}
	if err = h.captures.UpdateStatus(r.Context(), *session.CaptureID, domain.CaptureStatusUploaded, nil, nil, &videoURL, nil, nil); err != nil {
		JSONError(w, 503, "CAPTURE_UPDATE_FAILED")
		return
	}
	_, err = h.pool.Exec(r.Context(), "UPDATE capture_sessions SET video_url=$2,raw_object_key=$3,upload_verified_at=NOW(),updated_at=NOW() WHERE id=$1", sid, videoURL, key)
	if err != nil {
		JSONError(w, 503, "VERIFIED_UPLOAD_PERSIST_FAILED")
		return
	}
	progress := 100
	_, err = h.stages.UpdateStage(r.Context(), sid, "UPLOAD_VERIFIED", domain.UpdatePipelineStageInput{Status: domain.StageStatusCompleted, ProgressPercentage: &progress})
	if err != nil {
		JSONError(w, 503, "UPLOAD_EVENT_PERSIST_FAILED")
		return
	}
	// Job ID is deterministic for idempotent recovery of a lost finalization response.
	job, err := h.jobs.CreateSessionJob(r.Context(), sid, domain.CreateJobInput{ProjectID: session.ProjectID, CaptureID: session.CaptureID})
	if err != nil {
		stableID := uuid.NewSHA1(uuid.NameSpaceURL, []byte("vastu:job:"+sid))
		if failed, lookupErr := h.jobs.GetJob(r.Context(), stableID); lookupErr == nil && failed != nil {
			_, _ = h.pool.Exec(r.Context(), "UPDATE capture_sessions SET job_id=$2 WHERE id=$1", sid, failed.ID)
		}
		JSONError(w, 503, "PROCESSING_SUBMISSION_FAILED: "+err.Error())
		return
	}
	if job.Stage == domain.JobStageFailed {
		_, _ = h.pool.Exec(r.Context(), "UPDATE capture_sessions SET job_id=$2 WHERE id=$1", sid, job.ID)
		JSONError(w, 409, "PROCESSING_FAILED: retry processing from the dashboard")
		return
	}
	_, err = tx.Exec(r.Context(), "UPDATE capture_sessions SET job_id=$2,updated_at=NOW() WHERE id=$1", sid, job.ID)
	if err == nil {
		err = tx.Commit(r.Context())
	}
	if err != nil {
		JSONError(w, 503, "JOB_BIND_FAILED")
		return
	}
	session, err = h.sessions.GetSessionByID(r.Context(), sid)
	if err != nil {
		JSONError(w, 503, "SESSION_LOOKUP_FAILED")
		return
	}
	JSONSuccess(w, 200, "Video verified in S3 and submitted for processing", session)
}

// RetryProcessing accepts the desktop user JWT and verifies project ownership.
func (h *MobileUploadHandler) RetryProcessing(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, 401, "UNAUTHORIZED")
		return
	}
	sid := chi.URLParam(r, "sessionId")
	tx, err := h.lock(r.Context(), sid)
	if err != nil {
		JSONError(w, 503, "SESSION_BUSY")
		return
	}
	defer tx.Rollback(r.Context())
	session, err := h.sessions.GetSessionByID(r.Context(), sid)
	if err != nil {
		JSONError(w, 404, "SESSION_NOT_FOUND")
		return
	}
	var permitted bool
	err = h.pool.QueryRow(r.Context(), "SELECT EXISTS(SELECT 1 FROM projects WHERE id=$1 AND (created_by=$2 OR org_id=$3))", session.ProjectID, claims.UserID, claims.OrgID).Scan(&permitted)
	if err != nil || !permitted {
		JSONError(w, 403, "PROJECT_ACCESS_DENIED")
		return
	}
	if session.UploadVerifiedAt == nil || session.CaptureID == nil || session.JobID == nil {
		JSONError(w, 409, "VERIFIED_UPLOAD_REQUIRED")
		return
	}
	previous, err := h.jobs.GetJob(r.Context(), *session.JobID)
	if err != nil {
		JSONError(w, 503, "JOB_LOOKUP_FAILED")
		return
	}
	if previous.Stage != domain.JobStageFailed {
		JSONSuccess(w, 200, "Processing already submitted", session)
		return
	}
	job, err := h.jobs.CreateRetrySessionJob(r.Context(), sid, domain.CreateJobInput{ProjectID: session.ProjectID, CaptureID: session.CaptureID})
	if err != nil {
		JSONError(w, 503, err.Error())
		return
	}
	_, err = tx.Exec(r.Context(), "UPDATE capture_sessions SET job_id=$2,updated_at=NOW() WHERE id=$1", sid, job.ID)
	if err == nil {
		_, err = tx.Exec(r.Context(), "UPDATE pipeline_stages SET status='PENDING',error_details=NULL,retry_count=retry_count+1,completed_at=NULL,job_id=$2 WHERE session_id=$1 AND status IN ('FAILED','RETRYING')", sid, job.ID)
	}
	if err == nil {
		err = tx.Commit(r.Context())
	}
	if err != nil {
		JSONError(w, 503, "RETRY_BIND_FAILED")
		return
	}
	session, _ = h.sessions.GetSessionByID(r.Context(), sid)
	JSONSuccess(w, 200, "Processing retry submitted", session)
}

func (h *MobileUploadHandler) ProjectViewer(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaimsFromContext(r.Context())
	if !ok {
		JSONError(w, 401, "UNAUTHORIZED")
		return
	}
	projectID, err := uuid.Parse(chi.URLParam(r, "projectId"))
	if err != nil {
		JSONError(w, 400, "INVALID_PROJECT_ID")
		return
	}
	var viewer string
	err = h.pool.QueryRow(r.Context(), `SELECT s.viewer_url FROM capture_sessions s JOIN processing_jobs j ON j.id=s.job_id JOIN projects p ON p.id=s.project_id
 WHERE s.project_id=$1 AND (p.created_by=$2 OR p.org_id=$3) AND s.status='COMPLETED' AND j.stage='completed' AND s.viewer_url IS NOT NULL AND s.upload_verified_at IS NOT NULL ORDER BY s.completed_at DESC LIMIT 1`, projectID, claims.UserID, claims.OrgID).Scan(&viewer)
	if err != nil {
		JSONError(w, 404, "VIEWER_NOT_READY: successful artifact generation is required")
		return
	}
	JSONSuccess(w, 200, "Verified viewer available", map[string]string{"viewing_url": viewer})
}
