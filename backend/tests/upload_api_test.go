package tests

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/handler"
	"vastu/backend/internal/middleware"
	"vastu/backend/internal/service"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type mockUploadRepo struct {
	sessions map[uuid.UUID]*domain.UploadSession
	chunks   map[uuid.UUID][]*domain.UploadChunk
}

func newMockUploadRepo() *mockUploadRepo {
	return &mockUploadRepo{
		sessions: make(map[uuid.UUID]*domain.UploadSession),
		chunks:   make(map[uuid.UUID][]*domain.UploadChunk),
	}
}

func (m *mockUploadRepo) CreateSession(ctx context.Context, session *domain.UploadSession) error {
	m.sessions[session.ID] = session
	return nil
}

func (m *mockUploadRepo) GetSessionByID(ctx context.Context, id uuid.UUID) (*domain.UploadSession, error) {
	s, ok := m.sessions[id]
	if !ok {
		return nil, domain.ErrUploadNotFound
	}
	return s, nil
}

func (m *mockUploadRepo) SaveChunk(ctx context.Context, chunk *domain.UploadChunk) error {
	m.chunks[chunk.SessionID] = append(m.chunks[chunk.SessionID], chunk)
	return nil
}

func (m *mockUploadRepo) ListChunksBySession(ctx context.Context, sessionID uuid.UUID) ([]*domain.UploadChunk, error) {
	return m.chunks[sessionID], nil
}

func (m *mockUploadRepo) UpdateSessionStatus(ctx context.Context, sessionID uuid.UUID, status domain.UploadStatus, uploadedChunks int) error {
	if s, ok := m.sessions[sessionID]; ok {
		s.Status = status
		s.UploadedChunks = uploadedChunks
	}
	return nil
}

type mockCaptureRepoForUpload struct {
	captures map[uuid.UUID]*domain.Capture
}

func (m *mockCaptureRepoForUpload) Create(ctx context.Context, c *domain.Capture) error {
	m.captures[c.ID] = c
	return nil
}

func (m *mockCaptureRepoForUpload) GetByID(ctx context.Context, id uuid.UUID) (*domain.Capture, error) {
	c, ok := m.captures[id]
	if !ok {
		return nil, domain.ErrCaptureNotFound
	}
	return c, nil
}

func (m *mockCaptureRepoForUpload) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.Capture, error) {
	return nil, nil
}

func (m *mockCaptureRepoForUpload) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.CaptureStatus, qualityScore *float64, manifestURL, videoURL, imuURL, lidarURL *string) error {
	return nil
}

func setupUploadRouter(tempDir string) (*chi.Mux, *mockUploadRepo, *mockCaptureRepoForUpload, uuid.UUID) {
	uploadRepo := newMockUploadRepo()
	captureRepo := &mockCaptureRepoForUpload{captures: make(map[uuid.UUID]*domain.Capture)}
	uploadSvc := service.NewUploadService(uploadRepo, captureRepo, tempDir)
	uploadHdl := handler.NewUploadHandler(uploadSvc)

	userID := uuid.New()
	r := chi.NewRouter()

	// Auth inject helper middleware for tests
	authMiddleware := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
			if req.Header.Get("Authorization") == "Bearer valid-token" {
				ctx := middleware.SetClaimsContext(req.Context(), &domain.TokenClaims{
					UserID:     userID,
					MemberRole: domain.RoleOrgAdmin,
				})
				next.ServeHTTP(w, req.WithContext(ctx))
			} else {
				next.ServeHTTP(w, req)
			}
		})
	}

	r.Use(authMiddleware)

	r.Post("/api/v1/uploads/init", uploadHdl.Init)
	r.Post("/api/v1/uploads/{sessionId}/chunks/{chunkIndex}", uploadHdl.UploadChunk)
	r.Get("/api/v1/uploads/{sessionId}/progress", uploadHdl.GetProgress)
	r.Post("/api/v1/uploads/{sessionId}/complete", uploadHdl.Complete)

	return r, uploadRepo, captureRepo, userID
}

func TestUploadAPI(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "vastu_upload_api_test_*")
	require.NoError(t, err)
	defer os.RemoveAll(tempDir)

	router, uploadRepo, captureRepo, _ := setupUploadRouter(tempDir)

	captureID := uuid.New()
	captureRepo.captures[captureID] = &domain.Capture{ID: captureID, ProjectID: uuid.New()}

	t.Run("POST /api/v1/uploads/init - Unauthorized without token returns 401", func(t *testing.T) {
		initPayload := domain.InitUploadInput{
			CaptureID:      &captureID,
			FileName:       "video.mp4",
			FileType:       "video",
			TotalSizeBytes: 1024 * 1024,
		}
		body, _ := json.Marshal(initPayload)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/uploads/init", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusUnauthorized, rr.Code)
	})

	var sessionID uuid.UUID

	t.Run("POST /api/v1/uploads/init - Successful session init returns 201", func(t *testing.T) {
		initPayload := domain.InitUploadInput{
			CaptureID:      &captureID,
			FileName:       "scan.mp4",
			FileType:       "video",
			TotalSizeBytes: 120 * 1024, // 120KB
			ChunkSizeBytes: 60 * 1024,  // 2 chunks: 60KB each
			TotalChunks:    2,
		}
		body, _ := json.Marshal(initPayload)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/uploads/init", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer valid-token")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusCreated, rr.Code)

		var resp map[string]interface{}
		err := json.Unmarshal(rr.Body.Bytes(), &resp)
		require.NoError(t, err)
		data := resp["data"].(map[string]interface{})
		sessionID, err = uuid.Parse(data["id"].(string))
		require.NoError(t, err)
		assert.NotEqual(t, uuid.Nil, sessionID)
	})

	// Sample file content (120KB MP4-like header)
	fileData := make([]byte, 120*1024)
	copy(fileData[0:8], []byte("\x00\x00\x00\x20ftypisom"))
	hasher := sha256.New()
	hasher.Write(fileData)
	finalChecksum := hex.EncodeToString(hasher.Sum(nil))

	chunk1Data := fileData[0 : 60*1024]
	chunk2Data := fileData[60*1024 : 120*1024]

	h1 := sha256.New()
	h1.Write(chunk1Data)
	c1Checksum := hex.EncodeToString(h1.Sum(nil))

	h2 := sha256.New()
	h2.Write(chunk2Data)
	c2Checksum := hex.EncodeToString(h2.Sum(nil))

	t.Run("POST /api/v1/uploads/{sessionId}/chunks/{chunkIndex} - Upload chunk 0", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/uploads/"+sessionID.String()+"/chunks/0", bytes.NewReader(chunk1Data))
		req.Header.Set("X-Chunk-SHA256", c1Checksum)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)
	})

	t.Run("GET /api/v1/uploads/{sessionId}/progress - Progress reflects 1 chunk", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/uploads/"+sessionID.String()+"/progress", nil)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		var resp map[string]interface{}
		json.Unmarshal(rr.Body.Bytes(), &resp)
		data := resp["data"].(map[string]interface{})
		assert.Equal(t, float64(1), data["uploaded_chunks"])
		assert.Equal(t, float64(2), data["total_chunks"])
		assert.Len(t, data["missing_chunks"].([]interface{}), 1)
	})

	t.Run("POST /api/v1/uploads/{sessionId}/chunks/{chunkIndex} - Upload chunk 1", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/uploads/"+sessionID.String()+"/chunks/1", bytes.NewReader(chunk2Data))
		req.Header.Set("X-Chunk-SHA256", c2Checksum)
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)
	})

	t.Run("POST /api/v1/uploads/{sessionId}/complete - Finalize and verify clean promotion", func(t *testing.T) {
		completePayload := domain.CompleteUploadInput{
			FinalChecksumSHA256: &finalChecksum,
		}
		body, _ := json.Marshal(completePayload)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/uploads/"+sessionID.String()+"/complete", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusOK, rr.Code)

		// Verify session status updated
		session, err := uploadRepo.GetSessionByID(context.Background(), sessionID)
		require.NoError(t, err)
		assert.Equal(t, domain.UploadStatusCompleted, session.Status)
	})

	t.Run("POST /api/v1/uploads/{sessionId}/complete - Checksum mismatch fails", func(t *testing.T) {
		// New session with checksum mismatch
		badSessionID := uuid.New()
		uploadRepo.CreateSession(context.Background(), &domain.UploadSession{
			ID:                badSessionID,
			TotalChunks:       1,
			UploadedChunks:    1,
			TargetStoragePath: filepath.Join(tempDir, "quarantine", "dummy.bin"),
		})
		// Write dummy file
		_ = os.WriteFile(filepath.Join(tempDir, "quarantine", "dummy.bin"), []byte("data"), 0644)

		badChecksum := "0000000000000000000000000000000000000000000000000000000000000000"
		completePayload := domain.CompleteUploadInput{
			FinalChecksumSHA256: &badChecksum,
		}
		body, _ := json.Marshal(completePayload)
		req := httptest.NewRequest(http.MethodPost, "/api/v1/uploads/"+badSessionID.String()+"/complete", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		rr := httptest.NewRecorder()

		router.ServeHTTP(rr, req)
		assert.Equal(t, http.StatusBadRequest, rr.Code)
	})
}
