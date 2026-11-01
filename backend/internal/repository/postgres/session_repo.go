package postgres

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"vastu/backend/internal/domain"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type SessionRepository struct {
	pool *pgxpool.Pool
}

func NewSessionRepository(pool *pgxpool.Pool) *SessionRepository {
	return &SessionRepository{pool: pool}
}

// ----------------------------------------------------
// Capture Sessions
// ----------------------------------------------------

func (r *SessionRepository) CreateSession(ctx context.Context, session *domain.CaptureSession) error {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)
	query := `
		INSERT INTO capture_sessions (
			id, session_code, project_id, floor_id, room_id, room_name,
			operator_name, challenge_token, nonce, status, expires_at, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
	`
	now := time.Now()
	_, err = tx.Exec(
		ctx, query,
		session.ID, session.SessionCode, session.ProjectID, session.FloorID, session.RoomID,
		session.RoomName, session.OperatorName, session.ChallengeToken, session.Nonce,
		session.Status, session.ExpiresAt, now, now,
	)
	if err != nil {
		return fmt.Errorf("failed to insert capture session: %w", err)
	}

	// Initialize the 18 standard pipeline stages for this session in pending state
	for idx, stageName := range domain.StandardPipelineStages {
		worker := "Backend Control Plane"
		status := domain.StageStatusPending
		var startedAt *time.Time

		// First 3 stages default to completed or running upon session creation
		if stageName == "PROJECT_CREATED" || stageName == "ROOM_CREATED" {
			status = domain.StageStatusCompleted
			t := now
			startedAt = &t
		} else if stageName == "QR_SESSION_GENERATED" {
			status = domain.StageStatusCompleted
			t := now
			startedAt = &t
		}

		stageQuery := `
			INSERT INTO pipeline_stages (
				session_id, stage_name, stage_order, status, progress_percentage,
				responsible_worker, started_at, completed_at, updated_at
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
			ON CONFLICT (session_id, stage_name) DO NOTHING
		`
		var completedAt *time.Time
		if status == domain.StageStatusCompleted {
			completedAt = startedAt
		}
		progress := 0
		if status == domain.StageStatusCompleted {
			progress = 100
		}
		if _, err := tx.Exec(ctx, stageQuery, session.ID, stageName, idx+1, status, progress, worker, startedAt, completedAt, now); err != nil {
			return err
		}
	}

	return tx.Commit(ctx)
}

func (r *SessionRepository) GetSessionByID(ctx context.Context, sessionID string) (*domain.CaptureSession, error) {
	query := `
		SELECT s.id, s.session_code, s.project_id, COALESCE(p.name, 'VĀSTU Project') AS project_name,
		       s.floor_id, COALESCE(l.level_name, 'Floor 1') AS floor_name,
		       s.room_id, s.room_name, s.operator_name, s.challenge_token, s.nonce,
		       s.grant_token, s.device_id, s.status, s.expires_at, s.redeemed_at,
		       s.completed_at, s.capture_package_url, s.quality_summary, s.created_at, s.updated_at, s.capture_id, s.upload_id, s.job_id, s.video_url, s.raw_object_key, s.upload_verified_at, s.viewer_url
		FROM capture_sessions s
		LEFT JOIN projects p ON s.project_id = p.id
		LEFT JOIN spatial_levels l ON s.floor_id = l.id
		WHERE s.id = $1
	`
	row := r.pool.QueryRow(ctx, query, sessionID)
	var s domain.CaptureSession
	var qualityBytes []byte

	err := row.Scan(
		&s.ID, &s.SessionCode, &s.ProjectID, &s.ProjectName,
		&s.FloorID, &s.FloorName, &s.RoomID, &s.RoomName, &s.OperatorName,
		&s.ChallengeToken, &s.Nonce, &s.GrantToken, &s.DeviceID, &s.Status,
		&s.ExpiresAt, &s.RedeemedAt, &s.CompletedAt, &s.CapturePackageURL,
		&qualityBytes, &s.CreatedAt, &s.UpdatedAt, &s.CaptureID, &s.UploadID, &s.JobID, &s.VideoURL, &s.RawObjectKey, &s.UploadVerifiedAt, &s.ViewerURL,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("capture session not found")
		}
		return nil, err
	}

	if len(qualityBytes) > 0 {
		_ = json.Unmarshal(qualityBytes, &s.QualitySummary)
	}

	// Auto-expire if past expiry date and still CREATED
	if s.Status == domain.SessionStatusCreated && time.Now().After(s.ExpiresAt) {
		s.Status = domain.SessionStatusExpired
		_, _ = r.pool.Exec(ctx, "UPDATE capture_sessions SET status = $1, updated_at = NOW() WHERE id = $2", domain.SessionStatusExpired, s.ID)
	}

	return &s, nil
}

func (r *SessionRepository) GetSessionByChallenge(ctx context.Context, challengeToken string) (*domain.CaptureSession, error) {
	query := `
		SELECT s.id, s.session_code, s.project_id, COALESCE(p.name, 'VĀSTU Project') AS project_name,
		       s.floor_id, COALESCE(l.level_name, 'Floor 1') AS floor_name,
		       s.room_id, s.room_name, s.operator_name, s.challenge_token, s.nonce,
		       s.grant_token, s.device_id, s.status, s.expires_at, s.redeemed_at,
		       s.completed_at, s.capture_package_url, s.quality_summary, s.created_at, s.updated_at, s.capture_id, s.upload_id, s.job_id, s.video_url, s.raw_object_key, s.upload_verified_at, s.viewer_url
		FROM capture_sessions s
		LEFT JOIN projects p ON s.project_id = p.id
		LEFT JOIN spatial_levels l ON s.floor_id = l.id
		WHERE s.challenge_token = $1
	`
	row := r.pool.QueryRow(ctx, query, challengeToken)
	var s domain.CaptureSession
	var qualityBytes []byte

	err := row.Scan(
		&s.ID, &s.SessionCode, &s.ProjectID, &s.ProjectName,
		&s.FloorID, &s.FloorName, &s.RoomID, &s.RoomName, &s.OperatorName,
		&s.ChallengeToken, &s.Nonce, &s.GrantToken, &s.DeviceID, &s.Status,
		&s.ExpiresAt, &s.RedeemedAt, &s.CompletedAt, &s.CapturePackageURL,
		&qualityBytes, &s.CreatedAt, &s.UpdatedAt, &s.CaptureID, &s.UploadID, &s.JobID, &s.VideoURL, &s.RawObjectKey, &s.UploadVerifiedAt, &s.ViewerURL,
	)
	if err != nil {
		return nil, err
	}
	if len(qualityBytes) > 0 {
		_ = json.Unmarshal(qualityBytes, &s.QualitySummary)
	}
	return &s, nil
}

func (r *SessionRepository) ListSessionsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.CaptureSession, error) {
	query := `
		SELECT s.id, s.session_code, s.project_id, COALESCE(p.name, 'VĀSTU Project') AS project_name,
		       s.floor_id, COALESCE(l.level_name, 'Floor 1') AS floor_name,
		       s.room_id, s.room_name, s.operator_name, s.challenge_token, s.nonce,
		       s.grant_token, s.device_id, s.status, s.expires_at, s.redeemed_at,
		       s.completed_at, s.capture_package_url, s.quality_summary, s.created_at, s.updated_at, s.capture_id, s.upload_id, s.job_id, s.video_url, s.raw_object_key, s.upload_verified_at, s.viewer_url
		FROM capture_sessions s
		LEFT JOIN projects p ON s.project_id = p.id
		LEFT JOIN spatial_levels l ON s.floor_id = l.id
		WHERE s.project_id = $1
		ORDER BY s.created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.CaptureSession
	now := time.Now()
	for rows.Next() {
		var s domain.CaptureSession
		var qualityBytes []byte
		if err := rows.Scan(
			&s.ID, &s.SessionCode, &s.ProjectID, &s.ProjectName,
			&s.FloorID, &s.FloorName, &s.RoomID, &s.RoomName, &s.OperatorName,
			&s.ChallengeToken, &s.Nonce, &s.GrantToken, &s.DeviceID, &s.Status,
			&s.ExpiresAt, &s.RedeemedAt, &s.CompletedAt, &s.CapturePackageURL,
			&qualityBytes, &s.CreatedAt, &s.UpdatedAt, &s.CaptureID, &s.UploadID, &s.JobID, &s.VideoURL, &s.RawObjectKey, &s.UploadVerifiedAt, &s.ViewerURL,
		); err != nil {
			return nil, err
		}
		if s.Status == domain.SessionStatusCreated && now.After(s.ExpiresAt) {
			s.Status = domain.SessionStatusExpired
		}
		if len(qualityBytes) > 0 {
			_ = json.Unmarshal(qualityBytes, &s.QualitySummary)
		}
		list = append(list, &s)
	}
	return list, nil
}

func (r *SessionRepository) ListAllSessions(ctx context.Context) ([]*domain.CaptureSession, error) {
	query := `
		SELECT s.id, s.session_code, s.project_id, COALESCE(p.name, 'VĀSTU Project') AS project_name,
		       s.floor_id, COALESCE(l.level_name, 'Floor 1') AS floor_name,
		       s.room_id, s.room_name, s.operator_name, s.challenge_token, s.nonce,
		       s.grant_token, s.device_id, s.status, s.expires_at, s.redeemed_at,
		       s.completed_at, s.capture_package_url, s.quality_summary, s.created_at, s.updated_at, s.capture_id, s.upload_id, s.job_id, s.video_url, s.raw_object_key, s.upload_verified_at, s.viewer_url
		FROM capture_sessions s
		LEFT JOIN projects p ON s.project_id = p.id
		LEFT JOIN spatial_levels l ON s.floor_id = l.id
		ORDER BY s.created_at DESC
		LIMIT 100
	`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.CaptureSession
	now := time.Now()
	for rows.Next() {
		var s domain.CaptureSession
		var qualityBytes []byte
		if err := rows.Scan(
			&s.ID, &s.SessionCode, &s.ProjectID, &s.ProjectName,
			&s.FloorID, &s.FloorName, &s.RoomID, &s.RoomName, &s.OperatorName,
			&s.ChallengeToken, &s.Nonce, &s.GrantToken, &s.DeviceID, &s.Status,
			&s.ExpiresAt, &s.RedeemedAt, &s.CompletedAt, &s.CapturePackageURL,
			&qualityBytes, &s.CreatedAt, &s.UpdatedAt, &s.CaptureID, &s.UploadID, &s.JobID, &s.VideoURL, &s.RawObjectKey, &s.UploadVerifiedAt, &s.ViewerURL,
		); err != nil {
			return nil, err
		}
		if s.Status == domain.SessionStatusCreated && now.After(s.ExpiresAt) {
			s.Status = domain.SessionStatusExpired
		}
		if len(qualityBytes) > 0 {
			_ = json.Unmarshal(qualityBytes, &s.QualitySummary)
		}
		list = append(list, &s)
	}
	return list, nil
}

func (r *SessionRepository) UpdateSessionStatus(ctx context.Context, sessionID string, status domain.SessionStatus) error {
	_, err := r.pool.Exec(ctx, "UPDATE capture_sessions SET status = $1, updated_at = NOW() WHERE id = $2", status, sessionID)
	return err
}

func (r *SessionRepository) AuthorizeSession(ctx context.Context, sessionID, deviceID, grantToken string) error {
	now := time.Now()
	query := `
		UPDATE capture_sessions
		SET status = $1, device_id = $2, grant_token = $3, redeemed_at = $4, updated_at = $4
		WHERE id = $5 AND status = 'CREATED' AND expires_at > NOW()
	`
	result, err := r.pool.Exec(ctx, query, domain.SessionStatusAuthorized, deviceID, grantToken, now, sessionID)
	if err != nil {
		return err
	}
	if result.RowsAffected() != 1 {
		return errors.New("challenge expired or already redeemed")
	}
	return nil
}

// ----------------------------------------------------
// Devices & Heartbeats
// ----------------------------------------------------

func (r *SessionRepository) UpsertDevice(ctx context.Context, d *domain.Device) error {
	query := `
		INSERT INTO devices (
			device_uuid, device_model, device_os, app_version, battery_level,
			arkit_tracking_status, local_ai_status, network_type, current_session_id,
			current_project_id, current_room_id, last_heartbeat_at, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW(), NOW())
		ON CONFLICT (device_uuid) DO UPDATE SET
			device_model = EXCLUDED.device_model,
			device_os = EXCLUDED.device_os,
			app_version = EXCLUDED.app_version,
			battery_level = CASE WHEN EXCLUDED.battery_level >= 0 THEN EXCLUDED.battery_level ELSE devices.battery_level END,
			arkit_tracking_status = EXCLUDED.arkit_tracking_status,
			local_ai_status = EXCLUDED.local_ai_status,
			network_type = EXCLUDED.network_type,
			current_session_id = COALESCE(EXCLUDED.current_session_id, devices.current_session_id),
			current_project_id = COALESCE(EXCLUDED.current_project_id, devices.current_project_id),
			current_room_id = COALESCE(EXCLUDED.current_room_id, devices.current_room_id),
			last_heartbeat_at = NOW(),
			updated_at = NOW()
	`
	_, err := r.pool.Exec(
		ctx, query,
		d.DeviceUUID, d.DeviceModel, d.DeviceOS, d.AppVersion, d.BatteryLevel,
		d.ARKitTrackingStatus, d.LocalAIStatus, d.NetworkType, d.CurrentSessionID,
		d.CurrentProjectID, d.CurrentRoomID,
	)
	return err
}

func (r *SessionRepository) RecordHeartbeat(ctx context.Context, hb *domain.DeviceHeartbeatInput) error {
	// 1. Insert into device_heartbeats telemetry log
	insertQuery := `
		INSERT INTO device_heartbeats (
			device_uuid, session_id, battery_level, arkit_tracking_status,
			local_ai_status, recording_state, network_type, storage_free_mb, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
	`
	bat := -1.0
	if hb.BatteryLevel != nil {
		bat = *hb.BatteryLevel
	}
	_, err := r.pool.Exec(
		ctx, insertQuery,
		hb.DeviceUUID, hb.SessionID, bat, hb.ARKitTrackingStatus,
		hb.LocalAIStatus, hb.RecordingState, hb.NetworkType, hb.StorageFreeMB,
	)

	if err != nil {
		return err
	}
	// 2. Update device last heartbeat
	deviceUpdateQuery := `
		UPDATE devices
		SET last_heartbeat_at = NOW(),
		    battery_level = CASE WHEN $1 >= 0 THEN $1 ELSE battery_level END,
		    arkit_tracking_status = $2,
		    local_ai_status = $3,
		    network_type = $4,
		    current_session_id = COALESCE($5, current_session_id),
		    updated_at = NOW()
		WHERE device_uuid = $6
	`
	_, err = r.pool.Exec(ctx, deviceUpdateQuery, bat, hb.ARKitTrackingStatus, hb.LocalAIStatus, hb.NetworkType, hb.SessionID, hb.DeviceUUID)
	return err
}

func (r *SessionRepository) ListDevices(ctx context.Context) ([]*domain.Device, error) {
	query := `
		SELECT id, device_uuid, device_model, device_os, app_version, battery_level,
		       arkit_tracking_status, local_ai_status, network_type, current_session_id,
		       current_project_id, current_room_id, last_heartbeat_at, created_at, updated_at
		FROM devices
		ORDER BY last_heartbeat_at DESC
	`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.Device
	now := time.Now()
	for rows.Next() {
		var d domain.Device
		if err := rows.Scan(
			&d.ID, &d.DeviceUUID, &d.DeviceModel, &d.DeviceOS, &d.AppVersion,
			&d.BatteryLevel, &d.ARKitTrackingStatus, &d.LocalAIStatus, &d.NetworkType,
			&d.CurrentSessionID, &d.CurrentProjectID, &d.CurrentRoomID,
			&d.LastHeartbeatAt, &d.CreatedAt, &d.UpdatedAt,
		); err != nil {
			return nil, err
		}

		// Requirement: Derive connection status from recent heartbeat activity (< 30 seconds)
		if now.Sub(d.LastHeartbeatAt) <= 30*time.Second {
			d.Status = domain.DeviceStatusOnline
		} else {
			d.Status = domain.DeviceStatusOffline
		}
		list = append(list, &d)
	}
	return list, nil
}

// ----------------------------------------------------
// Pipeline Stages & Events
// ----------------------------------------------------

func (r *SessionRepository) GetPipelineStages(ctx context.Context, sessionID string) ([]*domain.PipelineStageRecord, error) {
	query := `
		SELECT id, session_id, job_id, stage_name, stage_order, status,
		       progress_percentage, COALESCE(responsible_worker, ''), error_details, retry_count,
		       started_at, completed_at, updated_at
		FROM pipeline_stages
		WHERE session_id = $1
		ORDER BY stage_order ASC
	`
	rows, err := r.pool.Query(ctx, query, sessionID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	stages := make([]*domain.PipelineStageRecord, 0)
	for rows.Next() {
		var s domain.PipelineStageRecord
		if err := rows.Scan(
			&s.ID, &s.SessionID, &s.JobID, &s.StageName, &s.StageOrder, &s.Status,
			&s.ProgressPercentage, &s.ResponsibleWorker, &s.ErrorDetails, &s.RetryCount,
			&s.StartedAt, &s.CompletedAt, &s.UpdatedAt,
		); err != nil {
			return nil, err
		}
		stages = append(stages, &s)
	}
	return stages, rows.Err()
}

const updatePipelineStageSQL = `
		UPDATE pipeline_stages
		SET status = $1::varchar,
		    progress_percentage = COALESCE($2, progress_percentage),
		    responsible_worker = COALESCE($3, responsible_worker),
		    error_details = COALESCE($4, error_details),
		    started_at = CASE WHEN $5::timestamptz IS NOT NULL AND started_at IS NULL THEN $5 ELSE started_at END,
		    completed_at = CASE WHEN $6::timestamptz IS NOT NULL THEN $6 ELSE completed_at END,
		    retry_count = CASE WHEN $1::varchar = 'RETRYING' THEN retry_count + 1 ELSE retry_count END,
		    updated_at = NOW()
		WHERE session_id = $7 AND stage_name = $8
		RETURNING id, session_id, job_id, stage_name, stage_order, status,
		          progress_percentage, COALESCE(responsible_worker, ''), error_details, retry_count,
		          started_at, completed_at, updated_at
	`

func (r *SessionRepository) UpdatePipelineStage(
	ctx context.Context,
	sessionID string,
	stageName string,
	input domain.UpdatePipelineStageInput,
) (*domain.PipelineStageRecord, error) {
	now := time.Now()
	var setCompleted *time.Time
	var setStarted *time.Time

	if input.Status == domain.StageStatusRunning {
		setStarted = &now
	} else if input.Status == domain.StageStatusCompleted {
		setCompleted = &now
	}

	query := updatePipelineStageSQL
	row := r.pool.QueryRow(
		ctx, query,
		input.Status, input.ProgressPercentage, input.ResponsibleWorker, input.ErrorDetails,
		setStarted, setCompleted, sessionID, stageName,
	)

	var s domain.PipelineStageRecord
	if err := row.Scan(
		&s.ID, &s.SessionID, &s.JobID, &s.StageName, &s.StageOrder, &s.Status,
		&s.ProgressPercentage, &s.ResponsibleWorker, &s.ErrorDetails, &s.RetryCount,
		&s.StartedAt, &s.CompletedAt, &s.UpdatedAt,
	); err != nil {
		return nil, fmt.Errorf("failed to update pipeline stage: %w", err)
	}

	// Record durable event
	payloadBytes, _ := json.Marshal(input.Payload)
	eventQuery := `
		INSERT INTO pipeline_events (session_id, stage_name, event_type, payload, created_at)
		VALUES ($1, $2, $3, $4, NOW())
	`
	eventType := fmt.Sprintf("STAGE_%s", input.Status)
	_, _ = r.pool.Exec(ctx, eventQuery, sessionID, stageName, eventType, payloadBytes)

	return &s, nil
}

// ----------------------------------------------------
// Room Mapping
// ----------------------------------------------------

func (r *SessionRepository) ListRoomsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.RoomWithHierarchy, error) {
	query := `
		SELECT sec.id, sec.level_id, COALESCE(lvl.level_number, 0) AS level_number,
		       COALESCE(lvl.level_name, 'Floor 1') AS level_name,
		       p.id AS project_id, p.name AS project_name,
		       sec.name, sec.section_type, sec.area_sqm,
		       sec.capture_status, sec.provisional_floorplan_url, sec.dimensions_validated,
		       sec.coverage_percentage, sec.quality_score,
		       (
		           SELECT cs.id FROM capture_sessions cs
		           WHERE cs.room_id = sec.id AND cs.status IN ('CREATED', 'AUTHORIZED', 'RECORDING', 'UPLOADING')
		           ORDER BY cs.created_at DESC LIMIT 1
		       ) AS active_session_id,
		       (
		           SELECT cs.session_code FROM capture_sessions cs
		           WHERE cs.room_id = sec.id AND cs.status IN ('CREATED', 'AUTHORIZED', 'RECORDING', 'UPLOADING')
		           ORDER BY cs.created_at DESC LIMIT 1
		       ) AS active_session_code,
		       sec.last_capture_at, sec.rescan_requested,
		       (
		           SELECT COUNT(*) FROM capture_sessions cs WHERE cs.room_id = sec.id
		       ) AS capture_attempts_count
		FROM spatial_sections sec
		JOIN spatial_levels lvl ON sec.level_id = lvl.id
		JOIN project_structures st ON lvl.structure_id = st.id
		JOIN projects p ON st.project_id = p.id
		WHERE p.id = $1
		ORDER BY lvl.level_number ASC, sec.name ASC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.RoomWithHierarchy
	for rows.Next() {
		var rm domain.RoomWithHierarchy
		var dimsBytes []byte
		if err := rows.Scan(
			&rm.ID, &rm.LevelID, &rm.LevelNumber, &rm.LevelName,
			&rm.ProjectID, &rm.ProjectName, &rm.Name, &rm.SectionType, &rm.AreaSqm,
			&rm.CaptureStatus, &rm.ProvisionalFloorplanURL, &dimsBytes,
			&rm.CoveragePercentage, &rm.QualityScore,
			&rm.ActiveSessionID, &rm.ActiveSessionCode,
			&rm.LastCaptureAt, &rm.RescanRequested,
			&rm.CaptureAttemptsCount,
		); err != nil {
			return nil, err
		}
		if len(dimsBytes) > 0 {
			_ = json.Unmarshal(dimsBytes, &rm.DimensionsValidated)
		}
		list = append(list, &rm)
	}
	return list, nil
}

func (r *SessionRepository) CreateRoom(ctx context.Context, floorID uuid.UUID, input domain.CreateRoomInput) (*domain.RoomWithHierarchy, error) {
	query := `
		INSERT INTO spatial_sections (level_id, name, section_type, area_sqm, capture_status, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 'UNCAPTURED', NOW(), NOW())
		RETURNING id, level_id, name, section_type, area_sqm, capture_status
	`
	secType := input.SectionType
	if secType == "" {
		secType = "room"
	}
	row := r.pool.QueryRow(ctx, query, floorID, input.Name, secType, input.AreaSqm)
	var rm domain.RoomWithHierarchy
	if err := row.Scan(&rm.ID, &rm.LevelID, &rm.Name, &rm.SectionType, &rm.AreaSqm, &rm.CaptureStatus); err != nil {
		return nil, err
	}
	return &rm, nil
}
