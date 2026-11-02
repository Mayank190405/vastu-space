package service

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"errors"
	"fmt"
	"net/url"
	"sync"
	"time"

	"vastu/backend/internal/domain"

	"github.com/google/uuid"
)

type CaptureSessionRepository interface {
	CreateSession(context.Context, *domain.CaptureSession) error
	GetSessionByID(context.Context, string) (*domain.CaptureSession, error)
	GetSessionByChallenge(context.Context, string) (*domain.CaptureSession, error)
	ListSessionsByProject(context.Context, uuid.UUID) ([]*domain.CaptureSession, error)
	ListAllSessions(context.Context) ([]*domain.CaptureSession, error)
	UpdateSessionStatus(context.Context, string, domain.SessionStatus) error
	AuthorizeSession(context.Context, string, string, string) error
	UpsertDevice(context.Context, *domain.Device) error
	RecordHeartbeat(context.Context, *domain.DeviceHeartbeatInput) error
	ListDevices(context.Context) ([]*domain.Device, error)
	GetPipelineStages(context.Context, string) ([]*domain.PipelineStageRecord, error)
	UpdatePipelineStage(context.Context, string, string, domain.UpdatePipelineStageInput) (*domain.PipelineStageRecord, error)
	ListRoomsByProject(context.Context, uuid.UUID) ([]*domain.RoomWithHierarchy, error)
	CreateRoom(context.Context, uuid.UUID, domain.CreateRoomInput) (*domain.RoomWithHierarchy, error)
}

type SessionManagerService struct {
	sessionRepo CaptureSessionRepository
	appURL      string

	// SSE subscriber broker
	subscribersLock sync.RWMutex
	subscribers     map[string][]chan domain.PipelineStageRecord
}

func NewSessionManagerService(sessionRepo CaptureSessionRepository, appURL string) *SessionManagerService {
	return &SessionManagerService{
		sessionRepo: sessionRepo,
		appURL:      appURL,
		subscribers: make(map[string][]chan domain.PipelineStageRecord),
	}
}

// ----------------------------------------------------
// QR Session Creation & Management
// ----------------------------------------------------

func (s *SessionManagerService) CreateCaptureSession(
	ctx context.Context,
	input domain.CreateCaptureSessionInput,
) (*domain.CaptureSession, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}
	if input.RoomName == "" {
		return nil, errors.New("room_name is required")
	}

	ttl := input.TTLMinutes
	if ttl <= 0 {
		ttl = 60 // 1 hour default
	}

	sessionUUID := uuid.New().String()
	sessionID := fmt.Sprintf("sess_%s", sessionUUID[:12])
	sessionCode := fmt.Sprintf("#S-%s", sessionUUID[:6])

	challengeBytes := make([]byte, 16)
	if _, err := rand.Read(challengeBytes); err != nil {
		return nil, err
	}
	challengeToken := fmt.Sprintf("chal_%s", hex.EncodeToString(challengeBytes))

	nonceBytes := make([]byte, 8)
	if _, err := rand.Read(nonceBytes); err != nil {
		return nil, err
	}
	nonce := hex.EncodeToString(nonceBytes)

	expiresAt := time.Now().Add(time.Duration(ttl) * time.Minute)

	// Build official vastu:// QR URI payload
	params := url.Values{}
	params.Set("endpoint", s.appURL)
	params.Set("session_id", sessionID)
	params.Set("challenge", challengeToken)
	params.Set("nonce", nonce)
	params.Set("project_id", input.ProjectID.String())
	params.Set("room_name", input.RoomName)
	if input.RoomID != nil {
		params.Set("room_id", input.RoomID.String())
	}
	if input.OperatorName != nil {
		params.Set("operator", *input.OperatorName)
	}
	params.Set("expires_at", fmt.Sprintf("%d", expiresAt.Unix()))

	qrPayload := fmt.Sprintf("vastu://capture-session?%s", params.Encode())

	session := &domain.CaptureSession{
		ID:             sessionID,
		SessionCode:    sessionCode,
		ProjectID:      input.ProjectID,
		FloorID:        input.FloorID,
		RoomID:         input.RoomID,
		RoomName:       input.RoomName,
		OperatorName:   input.OperatorName,
		ChallengeToken: challengeToken,
		Nonce:          nonce,
		Status:         domain.SessionStatusCreated,
		QRPayload:      qrPayload,
		ExpiresAt:      expiresAt,
	}

	if err := s.sessionRepo.CreateSession(ctx, session); err != nil {
		return nil, err
	}

	return session, nil
}

func (s *SessionManagerService) GetSession(ctx context.Context, sessionID string) (*domain.CaptureSession, error) {
	session, err := s.sessionRepo.GetSessionByID(ctx, sessionID)
	if err != nil {
		return nil, err
	}

	// Reconstruct QR payload
	params := url.Values{}
	params.Set("endpoint", s.appURL)
	params.Set("session_id", session.ID)
	params.Set("challenge", session.ChallengeToken)
	params.Set("nonce", session.Nonce)
	params.Set("project_id", session.ProjectID.String())
	params.Set("room_name", session.RoomName)
	if session.RoomID != nil {
		params.Set("room_id", session.RoomID.String())
	}
	if session.OperatorName != nil {
		params.Set("operator", *session.OperatorName)
	}
	params.Set("expires_at", fmt.Sprintf("%d", session.ExpiresAt.Unix()))
	session.QRPayload = fmt.Sprintf("vastu://capture-session?%s", params.Encode())

	return session, nil
}

func (s *SessionManagerService) ListSessionsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.CaptureSession, error) {
	return s.sessionRepo.ListSessionsByProject(ctx, projectID)
}

func (s *SessionManagerService) ListAllSessions(ctx context.Context) ([]*domain.CaptureSession, error) {
	return s.sessionRepo.ListAllSessions(ctx)
}

func (s *SessionManagerService) RevokeSession(ctx context.Context, sessionID string) error {
	session, err := s.sessionRepo.GetSessionByID(ctx, sessionID)
	if err != nil {
		return err
	}
	if session.Status == domain.SessionStatusCompleted {
		return errors.New("cannot revoke a completed session")
	}

	return s.sessionRepo.UpdateSessionStatus(ctx, sessionID, domain.SessionStatusRevoked)
}

func (s *SessionManagerService) CreateRescanSession(ctx context.Context, roomID uuid.UUID, operatorName *string) (*domain.CaptureSession, error) {
	// Find project and room hierarchy
	// Creates a new session tied to the same room without overwriting previous sessions
	sessionInput := domain.CreateCaptureSessionInput{
		RoomID:       &roomID,
		RoomName:     "Rescan Session",
		OperatorName: operatorName,
		TTLMinutes:   120,
	}
	return s.CreateCaptureSession(ctx, sessionInput)
}

// ----------------------------------------------------
// Challenge Redemption (Mobile App Gateway)
// ----------------------------------------------------

func (s *SessionManagerService) RedeemChallenge(
	ctx context.Context,
	input domain.RedeemChallengeInput,
) (*domain.RedeemChallengeResponse, error) {
	if input.ChallengeToken == "" {
		return nil, errors.New("challenge_token is required")
	}

	session, err := s.sessionRepo.GetSessionByChallenge(ctx, input.ChallengeToken)
	if err != nil {
		return nil, errors.New("invalid or unknown capture challenge")
	}
	if input.SessionID != session.ID || input.Nonce != session.Nonce || input.DeviceID == "" {
		return nil, errors.New("challenge session, nonce and device_id must match")
	}

	// 1. Enforce Expiry
	if time.Now().After(session.ExpiresAt) {
		_ = s.sessionRepo.UpdateSessionStatus(ctx, session.ID, domain.SessionStatusExpired)
		return nil, errors.New("session QR challenge has expired")
	}

	// 2. Anti-Replay: Prevent redemption of already authorized/completed sessions
	if session.Status != domain.SessionStatusCreated {
		return nil, errors.New("challenge token has already been redeemed (single-use protection)")
	}
	if session.Status == domain.SessionStatusRevoked {
		return nil, errors.New("session has been revoked by project administrator")
	}

	// 3. Register or update device
	device := &domain.Device{
		DeviceUUID:          input.DeviceID,
		DeviceModel:         input.DeviceModel,
		DeviceOS:            input.DeviceOS,
		AppVersion:          input.AppVersion,
		BatteryLevel:        -1.0,
		ARKitTrackingStatus: "NORMAL",
		LocalAIStatus:       "READY",
		NetworkType:         "WIFI",
		CurrentSessionID:    &session.ID,
		CurrentProjectID:    &session.ProjectID,
		CurrentRoomID:       session.RoomID,
	}
	if err := s.sessionRepo.UpsertDevice(ctx, device); err != nil {
		return nil, fmt.Errorf("failed to register device: %w", err)
	}

	// 4. Generate short-lived grant token
	grantTokenBytes := make([]byte, 24)
	if _, err := rand.Read(grantTokenBytes); err != nil {
		return nil, err
	}
	grantToken := fmt.Sprintf("grant_%s", hex.EncodeToString(grantTokenBytes))

	// 5. Authorize session
	if err := s.sessionRepo.AuthorizeSession(ctx, session.ID, input.DeviceID, grantToken); err != nil {
		return nil, fmt.Errorf("failed to authorize session: %w", err)
	}

	// Advance pipeline stages: DEVICE_CONNECTED and SESSION_AUTHORIZED
	workerName := fmt.Sprintf("%s (%s)", input.DeviceModel, input.DeviceID)
	_, _ = s.UpdateStage(ctx, session.ID, "DEVICE_CONNECTED", domain.UpdatePipelineStageInput{
		Status:            domain.StageStatusCompleted,
		ResponsibleWorker: &workerName,
	})
	_, _ = s.UpdateStage(ctx, session.ID, "SESSION_AUTHORIZED", domain.UpdatePipelineStageInput{
		Status:            domain.StageStatusCompleted,
		ResponsibleWorker: &workerName,
	})

	roomIDStr := ""
	if session.RoomID != nil {
		roomIDStr = session.RoomID.String()
	}

	return &domain.RedeemChallengeResponse{
		SessionID:          session.ID,
		GrantToken:         grantToken,
		ProjectID:          session.ProjectID.String(),
		ProjectName:        session.ProjectName,
		RoomID:             roomIDStr,
		RoomName:           session.RoomName,
		Status:             string(domain.SessionStatusAuthorized),
		MaxDurationSeconds: 600,
	}, nil
}

// ----------------------------------------------------
// Devices & Heartbeats
// ----------------------------------------------------

func (s *SessionManagerService) RegisterDevice(ctx context.Context, d *domain.Device) error {
	return s.sessionRepo.UpsertDevice(ctx, d)
}

func (s *SessionManagerService) ProcessHeartbeat(ctx context.Context, hb *domain.DeviceHeartbeatInput) error {
	return s.sessionRepo.RecordHeartbeat(ctx, hb)
}

func (s *SessionManagerService) ListConnectedDevices(ctx context.Context) ([]*domain.Device, error) {
	return s.sessionRepo.ListDevices(ctx)
}

// ----------------------------------------------------
// Real-Time Pipeline Stages & SSE
// ----------------------------------------------------

func (s *SessionManagerService) GetPipelineStages(ctx context.Context, sessionID string) ([]*domain.PipelineStageRecord, error) {
	return s.sessionRepo.GetPipelineStages(ctx, sessionID)
}

func (s *SessionManagerService) UpdateStage(
	ctx context.Context,
	sessionID string,
	stageName string,
	input domain.UpdatePipelineStageInput,
) (*domain.PipelineStageRecord, error) {
	validStage := false
	for _, stage := range domain.StandardPipelineStages {
		if stage == stageName {
			validStage = true
			break
		}
	}
	if !validStage {
		return nil, errors.New("unknown pipeline stage")
	}
	switch input.Status {
	case domain.StageStatusPending, domain.StageStatusRunning, domain.StageStatusCompleted, domain.StageStatusFailed, domain.StageStatusRetrying, domain.StageStatusCancelled, domain.StageStatusSkipped:
	default:
		return nil, errors.New("invalid pipeline stage status")
	}
	if input.ProgressPercentage != nil && (*input.ProgressPercentage < 0 || *input.ProgressPercentage > 100) {
		return nil, errors.New("progress_percentage must be between 0 and 100")
	}
	updated, err := s.sessionRepo.UpdatePipelineStage(ctx, sessionID, stageName, input)
	if err != nil {
		return nil, err
	}

	// Broadcast stage update to active SSE subscribers
	s.broadcastStageUpdate(sessionID, *updated)
	return updated, nil
}

func (s *SessionManagerService) SubscribeStages(sessionID string) (chan domain.PipelineStageRecord, func()) {
	ch := make(chan domain.PipelineStageRecord, 16)
	s.subscribersLock.Lock()
	s.subscribers[sessionID] = append(s.subscribers[sessionID], ch)
	s.subscribersLock.Unlock()

	unsubscribe := func() {
		s.subscribersLock.Lock()
		defer s.subscribersLock.Unlock()
		list := s.subscribers[sessionID]
		for i, c := range list {
			if c == ch {
				s.subscribers[sessionID] = append(list[:i], list[i+1:]...)
				close(ch)
				break
			}
		}
	}

	return ch, unsubscribe
}

func (s *SessionManagerService) broadcastStageUpdate(sessionID string, record domain.PipelineStageRecord) {
	s.subscribersLock.RLock()
	defer s.subscribersLock.RUnlock()

	for _, ch := range s.subscribers[sessionID] {
		select {
		case ch <- record:
		default:
		}
	}
}

// ----------------------------------------------------
// Room Mapping
// ----------------------------------------------------

func (s *SessionManagerService) ListRoomsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.RoomWithHierarchy, error) {
	return s.sessionRepo.ListRoomsByProject(ctx, projectID)
}

func (s *SessionManagerService) CreateRoom(ctx context.Context, floorID uuid.UUID, input domain.CreateRoomInput) (*domain.RoomWithHierarchy, error) {
	return s.sessionRepo.CreateRoom(ctx, floorID, input)
}

// ValidateGrant checks the persisted grant and its session scope on every mobile request.
func (s *SessionManagerService) ValidateGrant(ctx context.Context, sessionID, token string) (*domain.CaptureSession, error) {
	session, err := s.sessionRepo.GetSessionByID(ctx, sessionID)
	if err != nil {
		return nil, errors.New("invalid capture session")
	}
	if session.ID != sessionID || token == "" || session.GrantToken == nil || subtle.ConstantTimeCompare([]byte(token), []byte(*session.GrantToken)) != 1 {
		return nil, errors.New("invalid session grant")
	}
	if time.Now().After(session.ExpiresAt) || session.Status == domain.SessionStatusRevoked || session.Status == domain.SessionStatusExpired || session.Status == domain.SessionStatusCreated {
		return nil, errors.New("session grant expired or revoked")
	}
	return session, nil
}
