package tests

import (
	"context"
	"errors"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"vastu/backend/internal/domain"
	"vastu/backend/internal/handler"
	"vastu/backend/internal/service"
)

type sessionContractRepo struct {
	service.CaptureSessionRepository
	session   *domain.CaptureSession
	lookupErr error
}

func (m *sessionContractRepo) GetSessionByID(context.Context, string) (*domain.CaptureSession, error) {
	if m.lookupErr != nil {
		return nil, m.lookupErr
	}
	return m.session, nil
}
func (m *sessionContractRepo) GetSessionByChallenge(context.Context, string) (*domain.CaptureSession, error) {
	if m.lookupErr != nil {
		return nil, m.lookupErr
	}
	return m.session, nil
}

func TestUnknownChallengeNeverCreatesGrant(t *testing.T) {
	repo := &sessionContractRepo{lookupErr: errors.New("not found")}
	svc := service.NewSessionManagerService(repo, "https://example.test")
	response, err := svc.RedeemChallenge(context.Background(), domain.RedeemChallengeInput{ChallengeToken: "invented"})
	require.Error(t, err)
	require.Nil(t, response)
}
func TestRedemptionRequiresMatchingSessionAndNonce(t *testing.T) {
	repo := &sessionContractRepo{session: &domain.CaptureSession{ID: "sess_real", Nonce: "real_nonce", ExpiresAt: time.Now().Add(time.Hour)}}
	svc := service.NewSessionManagerService(repo, "https://example.test")
	for _, input := range []domain.RedeemChallengeInput{
		{ChallengeToken: "challenge", SessionID: "sess_wrong", Nonce: "real_nonce", DeviceID: "phone"},
		{ChallengeToken: "challenge", SessionID: "sess_real", Nonce: "wrong", DeviceID: "phone"},
	} {
		response, err := svc.RedeemChallenge(context.Background(), input)
		require.Error(t, err)
		require.Nil(t, response)
	}
}
func TestMobileGrantScopeAndServerOwnedStages(t *testing.T) {
	grant := "grant_real"
	repo := &sessionContractRepo{session: &domain.CaptureSession{ID: "sess_real", GrantToken: &grant, Status: domain.SessionStatusAuthorized, ExpiresAt: time.Now().Add(time.Hour)}}
	h := handler.NewSessionManagementHandler(service.NewSessionManagerService(repo, "https://example.test"))
	router := chi.NewRouter()
	router.With(h.AuthenticateGrant).Post("/capture-sessions/{sessionId}/stages/{stageName}", h.UpdateMobileStage)
	router.With(h.AuthenticateGrant).Post("/capture-sessions/{sessionId}/finalize", h.FinalizeSession)
	for _, tc := range []struct {
		path, token string
		status      int
	}{
		{"/capture-sessions/sess_real/stages/COMPLETED", "grant_real", 403},
		{"/capture-sessions/sess_real/finalize", "grant_real", 409},
		{"/capture-sessions/sess_real/finalize", "invented", 401},
		{"/capture-sessions/sess_other/finalize", "grant_real", 401},
		{"/capture-sessions/sess_real/finalize", "", 401},
	} {
		req := httptest.NewRequest("POST", tc.path, strings.NewReader(`{}`))
		if tc.token != "" {
			req.Header.Set("Authorization", "Bearer "+tc.token)
		}
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)
		require.Equal(t, tc.status, recorder.Code, recorder.Body.String())
	}
	for _, status := range []domain.SessionStatus{domain.SessionStatusRevoked, domain.SessionStatusExpired, domain.SessionStatusCreated} {
		repo.session.Status = status
		_, err := service.NewSessionManagerService(repo, "").ValidateGrant(context.Background(), "sess_real", grant)
		require.Error(t, err)
	}
	repo.session.Status = domain.SessionStatusAuthorized
	repo.session.ExpiresAt = time.Now().Add(-time.Second)
	_, err := service.NewSessionManagerService(repo, "").ValidateGrant(context.Background(), "sess_real", grant)
	require.Error(t, err)
}

func TestUploadRejectsInconsistentChunkContract(t *testing.T) {
	svc := service.NewUploadService(newMockUploadRepo(), nil, t.TempDir())
	_, err := svc.InitSession(context.Background(), uuid.New(), domain.InitUploadInput{FileName: "video.mp4", TotalSizeBytes: 100, ChunkSizeBytes: 50, TotalChunks: 3})
	require.Error(t, err)
	session, err := svc.InitSession(context.Background(), uuid.New(), domain.InitUploadInput{FileName: "video.mp4", TotalSizeBytes: 100, ChunkSizeBytes: 50})
	require.NoError(t, err)
	_, err = svc.SaveChunk(context.Background(), session.ID, 0, "", strings.NewReader("short"))
	require.Error(t, err)
	progress, err := svc.GetProgress(context.Background(), session.ID)
	require.NoError(t, err)
	require.Equal(t, 0, progress.UploadedChunks)
}

func TestUploadCompletionSurvivesServiceRestart(t *testing.T) {
	repo := newMockUploadRepo()
	dir := t.TempDir()
	svc := service.NewUploadService(repo, nil, dir)
	contents := `{"capture":"real"}`
	session, err := svc.InitSession(context.Background(), uuid.New(), domain.InitUploadInput{FileName: "manifest.json", FileType: "manifest", TotalSizeBytes: int64(len(contents))})
	require.NoError(t, err)
	_, err = svc.SaveChunk(context.Background(), session.ID, 0, "", strings.NewReader(contents))
	require.NoError(t, err)
	firstURL, err := svc.CompleteUpload(context.Background(), session.ID, "")
	require.NoError(t, err)
	restarted := service.NewUploadService(repo, nil, dir)
	retryURL, err := restarted.CompleteUpload(context.Background(), session.ID, "")
	require.NoError(t, err)
	require.Equal(t, firstURL, retryURL)
	persisted, err := repo.GetSessionByID(context.Background(), session.ID)
	require.NoError(t, err)
	require.Contains(t, persisted.TargetStoragePath, "/clean/")
	require.NoError(t, os.Remove(persisted.TargetStoragePath))
	_, err = restarted.CompleteUpload(context.Background(), session.ID, "")
	require.Error(t, err)
}
