package postgres

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/geo"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)


// ==========================================
// 1. Capture Repository
// ==========================================

type CaptureRepo struct {
	pool *pgxpool.Pool
}

func NewCaptureRepo(pool *pgxpool.Pool) *CaptureRepo {
	return &CaptureRepo{pool: pool}
}

func (r *CaptureRepo) Create(ctx context.Context, c *domain.Capture) error {
	intrinsicsJSON, err := json.Marshal(c.CameraIntrinsics)
	if err != nil {
		intrinsicsJSON = []byte("{}")
	}

	query := `
		INSERT INTO captures (
			id, project_id, structure_id, level_id, section_id, operator_id,
			device_model, device_os, device_app_version, camera_intrinsics,
			imu_rate_hz, has_lidar, capture_mode, duration_seconds, frames_count,
			file_size_bytes, trajectory_length_meters, quality_score, blur_score,
			lighting_score, status, manifest_url, video_url, imu_url, lidar_url, notes,
			created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
			$16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28
		)
	`
	now := time.Now().UTC()
	c.CreatedAt = now
	c.UpdatedAt = now

	_, err = r.pool.Exec(ctx, query,
		c.ID, c.ProjectID, c.StructureID, c.LevelID, c.SectionID, c.OperatorID,
		c.DeviceModel, c.DeviceOS, c.DeviceAppVersion, intrinsicsJSON,
		c.IMURateHz, c.HasLiDAR, string(c.CaptureMode), c.DurationSeconds, c.FramesCount,
		c.FileSizeBytes, c.TrajectoryLengthMeters, c.QualityScore, c.BlurScore,
		c.LightingScore, string(c.Status), c.ManifestURL, c.VideoURL, c.IMUURL, c.LiDARURL, c.Notes,
		c.CreatedAt, c.UpdatedAt,
	)
	return err
}

func (r *CaptureRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.Capture, error) {
	query := `
		SELECT 
			id, project_id, structure_id, level_id, section_id, operator_id,
			device_model, device_os, device_app_version, camera_intrinsics,
			imu_rate_hz, has_lidar, capture_mode, duration_seconds, frames_count,
			file_size_bytes, trajectory_length_meters, quality_score, blur_score,
			lighting_score, status, manifest_url, video_url, imu_url, lidar_url, notes,
			created_at, updated_at
		FROM captures WHERE id = $1
	`
	c := &domain.Capture{}
	var intrinsicsBytes []byte
	var statusStr, modeStr string

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&c.ID, &c.ProjectID, &c.StructureID, &c.LevelID, &c.SectionID, &c.OperatorID,
		&c.DeviceModel, &c.DeviceOS, &c.DeviceAppVersion, &intrinsicsBytes,
		&c.IMURateHz, &c.HasLiDAR, &modeStr, &c.DurationSeconds, &c.FramesCount,
		&c.FileSizeBytes, &c.TrajectoryLengthMeters, &c.QualityScore, &c.BlurScore,
		&c.LightingScore, &statusStr, &c.ManifestURL, &c.VideoURL, &c.IMUURL, &c.LiDARURL, &c.Notes,
		&c.CreatedAt, &c.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("capture not found")
		}
		return nil, err
	}

	c.Status = domain.CaptureStatus(statusStr)
	c.CaptureMode = domain.CaptureMode(modeStr)
	if len(intrinsicsBytes) > 0 {
		var intrinsics domain.CameraIntrinsics
		if err := json.Unmarshal(intrinsicsBytes, &intrinsics); err == nil {
			c.CameraIntrinsics = &intrinsics
		}
	}

	return c, nil
}

func (r *CaptureRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.Capture, error) {
	query := `
		SELECT 
			id, project_id, structure_id, level_id, section_id, operator_id,
			device_model, device_os, device_app_version, camera_intrinsics,
			imu_rate_hz, has_lidar, capture_mode, duration_seconds, frames_count,
			file_size_bytes, trajectory_length_meters, quality_score, blur_score,
			lighting_score, status, manifest_url, video_url, imu_url, lidar_url, notes,
			created_at, updated_at
		FROM captures WHERE project_id = $1 ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.Capture
	for rows.Next() {
		c := &domain.Capture{}
		var intrinsicsBytes []byte
		var statusStr, modeStr string

		if err := rows.Scan(
			&c.ID, &c.ProjectID, &c.StructureID, &c.LevelID, &c.SectionID, &c.OperatorID,
			&c.DeviceModel, &c.DeviceOS, &c.DeviceAppVersion, &intrinsicsBytes,
			&c.IMURateHz, &c.HasLiDAR, &modeStr, &c.DurationSeconds, &c.FramesCount,
			&c.FileSizeBytes, &c.TrajectoryLengthMeters, &c.QualityScore, &c.BlurScore,
			&c.LightingScore, &statusStr, &c.ManifestURL, &c.VideoURL, &c.IMUURL, &c.LiDARURL, &c.Notes,
			&c.CreatedAt, &c.UpdatedAt,
		); err != nil {
			return nil, err
		}

		c.Status = domain.CaptureStatus(statusStr)
		c.CaptureMode = domain.CaptureMode(modeStr)
		if len(intrinsicsBytes) > 0 {
			var intrinsics domain.CameraIntrinsics
			if err := json.Unmarshal(intrinsicsBytes, &intrinsics); err == nil {
				c.CameraIntrinsics = &intrinsics
			}
		}
		list = append(list, c)
	}

	return list, nil
}

func (r *CaptureRepo) UpdateStatus(ctx context.Context, id uuid.UUID, status domain.CaptureStatus, qualityScore *float64, manifestURL, videoURL, imuURL, lidarURL *string) error {
	query := `
		UPDATE captures SET
			status = $2,
			quality_score = COALESCE($3, quality_score),
			manifest_url = COALESCE($4, manifest_url),
			video_url = COALESCE($5, video_url),
			imu_url = COALESCE($6, imu_url),
			lidar_url = COALESCE($7, lidar_url),
			updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query, id, string(status), qualityScore, manifestURL, videoURL, imuURL, lidarURL)
	return err
}

// ==========================================
// 2. Upload Repository
// ==========================================

type UploadRepo struct {
	pool *pgxpool.Pool
}

func NewUploadRepo(pool *pgxpool.Pool) *UploadRepo {
	return &UploadRepo{pool: pool}
}

func (r *UploadRepo) CreateSession(ctx context.Context, s *domain.UploadSession) error {
	query := `
		INSERT INTO upload_sessions (
			id, capture_id, user_id, file_name, file_type, total_size_bytes,
			chunk_size_bytes, total_chunks, uploaded_chunks, sha256_checksum,
			target_storage_path, status, expires_at, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
	`
	now := time.Now().UTC()
	s.CreatedAt = now
	s.UpdatedAt = now
	if s.ExpiresAt.IsZero() {
		s.ExpiresAt = now.Add(24 * time.Hour)
	}

	_, err := r.pool.Exec(ctx, query,
		s.ID, s.CaptureID, s.UserID, s.FileName, s.FileType, s.TotalSizeBytes,
		s.ChunkSizeBytes, s.TotalChunks, s.UploadedChunks, s.SHA256Checksum,
		s.TargetStoragePath, string(s.Status), s.ExpiresAt, s.CreatedAt, s.UpdatedAt,
	)
	return err
}

func (r *UploadRepo) GetSessionByID(ctx context.Context, id uuid.UUID) (*domain.UploadSession, error) {
	query := `
		SELECT 
			id, capture_id, user_id, file_name, file_type, total_size_bytes,
			chunk_size_bytes, total_chunks, uploaded_chunks, sha256_checksum,
			target_storage_path, status, expires_at, created_at, updated_at
		FROM upload_sessions WHERE id = $1
	`
	s := &domain.UploadSession{}
	var statusStr string

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&s.ID, &s.CaptureID, &s.UserID, &s.FileName, &s.FileType, &s.TotalSizeBytes,
		&s.ChunkSizeBytes, &s.TotalChunks, &s.UploadedChunks, &s.SHA256Checksum,
		&s.TargetStoragePath, &statusStr, &s.ExpiresAt, &s.CreatedAt, &s.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("upload session not found")
		}
		return nil, err
	}
	s.Status = domain.UploadStatus(statusStr)
	return s, nil
}

func (r *UploadRepo) SaveChunk(ctx context.Context, c *domain.UploadChunk) error {
	query := `
		INSERT INTO upload_chunks (
			id, session_id, chunk_index, size_bytes, sha256_hash, chunk_file_path, is_uploaded, uploaded_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		ON CONFLICT (session_id, chunk_index) DO UPDATE SET
			size_bytes = EXCLUDED.size_bytes,
			sha256_hash = EXCLUDED.sha256_hash,
			chunk_file_path = EXCLUDED.chunk_file_path,
			uploaded_at = EXCLUDED.uploaded_at
	`
	if c.ID == uuid.Nil {
		c.ID = uuid.New()
	}
	if c.UploadedAt.IsZero() {
		c.UploadedAt = time.Now().UTC()
	}

	_, err := r.pool.Exec(ctx, query,
		c.ID, c.SessionID, c.ChunkIndex, c.SizeBytes, c.SHA256Hash, c.ChunkFilePath, c.IsUploaded, c.UploadedAt,
	)
	return err
}

func (r *UploadRepo) ListChunksBySession(ctx context.Context, sessionID uuid.UUID) ([]*domain.UploadChunk, error) {
	query := `
		SELECT id, session_id, chunk_index, size_bytes, sha256_hash, chunk_file_path, is_uploaded, uploaded_at
		FROM upload_chunks WHERE session_id = $1 ORDER BY chunk_index ASC
	`
	rows, err := r.pool.Query(ctx, query, sessionID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var chunks []*domain.UploadChunk
	for rows.Next() {
		c := &domain.UploadChunk{}
		if err := rows.Scan(
			&c.ID, &c.SessionID, &c.ChunkIndex, &c.SizeBytes, &c.SHA256Hash, &c.ChunkFilePath, &c.IsUploaded, &c.UploadedAt,
		); err != nil {
			return nil, err
		}
		chunks = append(chunks, c)
	}
	return chunks, nil
}

func (r *UploadRepo) UpdateSessionStatus(ctx context.Context, sessionID uuid.UUID, status domain.UploadStatus, uploadedChunks int) error {
	query := `
		UPDATE upload_sessions SET
			status = $2,
			uploaded_chunks = $3,
			updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query, sessionID, string(status), uploadedChunks)
	return err
}

// ==========================================
// 3. Job Repository
// ==========================================

type JobRepo struct {
	pool *pgxpool.Pool
}

func NewJobRepo(pool *pgxpool.Pool) *JobRepo {
	return &JobRepo{pool: pool}
}

func (r *JobRepo) Create(ctx context.Context, j *domain.ProcessingJob) error {
	durationsJSON, err := json.Marshal(j.StageDurations)
	if err != nil {
		durationsJSON = []byte("{}")
	}

	query := `
		INSERT INTO processing_jobs (
			id, project_id, capture_id, stage, progress_percentage, priority,
			worker_node_id, error_code, error_message, stage_durations, started_at, completed_at,
			created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
	`
	now := time.Now().UTC()
	j.CreatedAt = now
	j.UpdatedAt = now

	_, err = r.pool.Exec(ctx, query,
		j.ID, j.ProjectID, j.CaptureID, string(j.Stage), j.ProgressPercentage, j.Priority,
		j.WorkerNodeID, j.ErrorCode, j.ErrorMessage, durationsJSON, j.StartedAt, j.CompletedAt,
		j.CreatedAt, j.UpdatedAt,
	)
	return err
}

func (r *JobRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.ProcessingJob, error) {
	query := `
		SELECT 
			id, project_id, capture_id, stage, progress_percentage, priority,
			worker_node_id, error_code, error_message, stage_durations, started_at, completed_at,
			created_at, updated_at
		FROM processing_jobs WHERE id = $1
	`
	j := &domain.ProcessingJob{}
	var stageStr string
	var durationsBytes []byte

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&j.ID, &j.ProjectID, &j.CaptureID, &stageStr, &j.ProgressPercentage, &j.Priority,
		&j.WorkerNodeID, &j.ErrorCode, &j.ErrorMessage, &durationsBytes, &j.StartedAt, &j.CompletedAt,
		&j.CreatedAt, &j.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("processing job not found")
		}
		return nil, err
	}
	j.Stage = domain.JobStage(stageStr)
	if len(durationsBytes) > 0 {
		_ = json.Unmarshal(durationsBytes, &j.StageDurations)
	}
	return j, nil
}

func (r *JobRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ProcessingJob, error) {
	query := `
		SELECT 
			id, project_id, capture_id, stage, progress_percentage, priority,
			worker_node_id, error_code, error_message, stage_durations, started_at, completed_at,
			created_at, updated_at
		FROM processing_jobs WHERE project_id = $1 ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.ProcessingJob
	for rows.Next() {
		j := &domain.ProcessingJob{}
		var stageStr string
		var durationsBytes []byte

		if err := rows.Scan(
			&j.ID, &j.ProjectID, &j.CaptureID, &stageStr, &j.ProgressPercentage, &j.Priority,
			&j.WorkerNodeID, &j.ErrorCode, &j.ErrorMessage, &durationsBytes, &j.StartedAt, &j.CompletedAt,
			&j.CreatedAt, &j.UpdatedAt,
		); err != nil {
			return nil, err
		}
		j.Stage = domain.JobStage(stageStr)
		if len(durationsBytes) > 0 {
			_ = json.Unmarshal(durationsBytes, &j.StageDurations)
		}
		list = append(list, j)
	}
	return list, nil
}

func (r *JobRepo) UpdateProgress(ctx context.Context, id uuid.UUID, stage domain.JobStage, progress int, workerNodeID, errorCode, errorMessage *string) error {
	var completedAt *time.Time
	if stage == domain.JobStageCompleted || stage == domain.JobStageFailed {
		now := time.Now().UTC()
		completedAt = &now
	}

	query := `
		UPDATE processing_jobs SET
			stage = $2,
			progress_percentage = $3,
			worker_node_id = COALESCE($4, worker_node_id),
			error_code = $5,
			error_message = $6,
			completed_at = COALESCE($7, completed_at),
			updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query, id, string(stage), progress, workerNodeID, errorCode, errorMessage, completedAt)
	return err
}

func (r *JobRepo) AddLog(ctx context.Context, log *domain.JobLog) error {
	metaJSON, _ := json.Marshal(log.Meta)
	query := `
		INSERT INTO job_logs (id, job_id, stage, log_level, message, meta, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
	`
	if log.ID == uuid.Nil {
		log.ID = uuid.New()
	}
	if log.CreatedAt.IsZero() {
		log.CreatedAt = time.Now().UTC()
	}

	_, err := r.pool.Exec(ctx, query, log.ID, log.JobID, log.Stage, log.LogLevel, log.Message, metaJSON, log.CreatedAt)
	return err
}

func (r *JobRepo) ListLogs(ctx context.Context, jobID uuid.UUID) ([]*domain.JobLog, error) {
	query := `
		SELECT id, job_id, stage, log_level, message, meta, created_at
		FROM job_logs WHERE job_id = $1 ORDER BY created_at ASC
	`
	rows, err := r.pool.Query(ctx, query, jobID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var logs []*domain.JobLog
	for rows.Next() {
		l := &domain.JobLog{}
		var metaBytes []byte
		if err := rows.Scan(&l.ID, &l.JobID, &l.Stage, &l.LogLevel, &l.Message, &metaBytes, &l.CreatedAt); err != nil {
			return nil, err
		}
		if len(metaBytes) > 0 {
			_ = json.Unmarshal(metaBytes, &l.Meta)
		}
		logs = append(logs, l)
	}
	return logs, nil
}

// ==========================================
// 4. Model Repository
// ==========================================

type ModelRepo struct {
	pool *pgxpool.Pool
}

func NewModelRepo(pool *pgxpool.Pool) *ModelRepo {
	return &ModelRepo{pool: pool}
}

func (r *ModelRepo) Create(ctx context.Context, m *domain.SpatialModel) error {
	bboxJSON, _ := json.Marshal(m.BoundingBox)
	coordJSON, _ := json.Marshal(m.CoordinateFrame)

	query := `
		INSERT INTO spatial_models (
			id, project_id, level_id, section_id, version, title, description,
			bounding_box, coordinate_frame, total_vertices, total_faces, point_density_sqm,
			precision_deviation_cm, is_active_version, parent_model_id, is_immutable,
			lineage_depth, published_at, created_by, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
	`
	now := time.Now().UTC()
	m.CreatedAt = now
	m.UpdatedAt = now
	if m.LineageDepth == 0 {
		m.LineageDepth = 1
	}

	_, err := r.pool.Exec(ctx, query,
		m.ID, m.ProjectID, m.LevelID, m.SectionID, m.Version, m.Title, m.Description,
		bboxJSON, coordJSON, m.TotalVertices, m.TotalFaces, m.PointDensitySQM,
		m.PrecisionDeviationCM, m.IsActiveVersion, m.ParentModelID, m.IsImmutable,
		m.LineageDepth, m.PublishedAt, m.CreatedBy, m.CreatedAt, m.UpdatedAt,
	)
	return err
}

func (r *ModelRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialModel, error) {
	query := `
		SELECT 
			id, project_id, level_id, section_id, version, title, description,
			bounding_box, coordinate_frame, total_vertices, total_faces, point_density_sqm,
			precision_deviation_cm, is_active_version, parent_model_id, is_immutable,
			lineage_depth, published_at, created_by, created_at, updated_at
		FROM spatial_models WHERE id = $1
	`
	m := &domain.SpatialModel{}
	var bboxBytes, coordBytes []byte

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&m.ID, &m.ProjectID, &m.LevelID, &m.SectionID, &m.Version, &m.Title, &m.Description,
		&bboxBytes, &coordBytes, &m.TotalVertices, &m.TotalFaces, &m.PointDensitySQM,
		&m.PrecisionDeviationCM, &m.IsActiveVersion, &m.ParentModelID, &m.IsImmutable,
		&m.LineageDepth, &m.PublishedAt, &m.CreatedBy, &m.CreatedAt, &m.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("spatial model not found")
		}
		return nil, err
	}

	if len(bboxBytes) > 0 {
		_ = json.Unmarshal(bboxBytes, &m.BoundingBox)
	}
	if len(coordBytes) > 0 {
		_ = json.Unmarshal(coordBytes, &m.CoordinateFrame)
	}

	// Fetch artifacts
	artifacts, _ := r.ListArtifactsByModel(ctx, m.ID)
	m.Artifacts = artifacts

	return m, nil
}

func (r *ModelRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialModel, error) {
	query := `
		SELECT 
			id, project_id, level_id, section_id, version, title, description,
			bounding_box, coordinate_frame, total_vertices, total_faces, point_density_sqm,
			precision_deviation_cm, is_active_version, parent_model_id, is_immutable,
			lineage_depth, published_at, created_by, created_at, updated_at
		FROM spatial_models WHERE project_id = $1 ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.SpatialModel
	for rows.Next() {
		m := &domain.SpatialModel{}
		var bboxBytes, coordBytes []byte
		if err := rows.Scan(
			&m.ID, &m.ProjectID, &m.LevelID, &m.SectionID, &m.Version, &m.Title, &m.Description,
			&bboxBytes, &coordBytes, &m.TotalVertices, &m.TotalFaces, &m.PointDensitySQM,
			&m.PrecisionDeviationCM, &m.IsActiveVersion, &m.ParentModelID, &m.IsImmutable,
			&m.LineageDepth, &m.PublishedAt, &m.CreatedBy, &m.CreatedAt, &m.UpdatedAt,
		); err != nil {
			return nil, err
		}
		if len(bboxBytes) > 0 {
			_ = json.Unmarshal(bboxBytes, &m.BoundingBox)
		}
		if len(coordBytes) > 0 {
			_ = json.Unmarshal(coordBytes, &m.CoordinateFrame)
		}
		list = append(list, m)
	}
	return list, nil
}

func (r *ModelRepo) GetActiveByProject(ctx context.Context, projectID uuid.UUID) (*domain.SpatialModel, error) {
	query := `
		SELECT 
			id, project_id, level_id, section_id, version, title, description,
			bounding_box, coordinate_frame, total_vertices, total_faces, point_density_sqm,
			precision_deviation_cm, is_active_version, parent_model_id, is_immutable,
			lineage_depth, published_at, created_by, created_at, updated_at
		FROM spatial_models WHERE project_id = $1 AND is_active_version = TRUE LIMIT 1
	`
	m := &domain.SpatialModel{}
	var bboxBytes, coordBytes []byte

	err := r.pool.QueryRow(ctx, query, projectID).Scan(
		&m.ID, &m.ProjectID, &m.LevelID, &m.SectionID, &m.Version, &m.Title, &m.Description,
		&bboxBytes, &coordBytes, &m.TotalVertices, &m.TotalFaces, &m.PointDensitySQM,
		&m.PrecisionDeviationCM, &m.IsActiveVersion, &m.ParentModelID, &m.IsImmutable,
		&m.LineageDepth, &m.PublishedAt, &m.CreatedBy, &m.CreatedAt, &m.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("no active spatial model found for project")
		}
		return nil, err
	}
	if len(bboxBytes) > 0 {
		_ = json.Unmarshal(bboxBytes, &m.BoundingBox)
	}
	if len(coordBytes) > 0 {
		_ = json.Unmarshal(coordBytes, &m.CoordinateFrame)
	}

	artifacts, _ := r.ListArtifactsByModel(ctx, m.ID)
	m.Artifacts = artifacts

	return m, nil
}

func (r *ModelRepo) SetActiveVersion(ctx context.Context, projectID uuid.UUID, modelID uuid.UUID) error {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	_, err = tx.Exec(ctx, `UPDATE spatial_models SET is_active_version = FALSE, updated_at = NOW() WHERE project_id = $1`, projectID)
	if err != nil {
		return err
	}

	res, err := tx.Exec(ctx, `UPDATE spatial_models SET is_active_version = TRUE, updated_at = NOW() WHERE id = $1 AND project_id = $2`, modelID, projectID)
	if err != nil {
		return err
	}
	if res.RowsAffected() == 0 {
		return errors.New("model not found in project")
	}

	return tx.Commit(ctx)
}

func (r *ModelRepo) PublishModel(ctx context.Context, modelID uuid.UUID) error {
	now := time.Now().UTC()
	query := `
		UPDATE spatial_models
		SET is_immutable = TRUE, published_at = $1, updated_at = $1
		WHERE id = $2
	`
	res, err := r.pool.Exec(ctx, query, now, modelID)
	if err != nil {
		return err
	}
	if res.RowsAffected() == 0 {
		return errors.New("spatial model not found")
	}
	return nil
}

func (r *ModelRepo) Update(ctx context.Context, m *domain.SpatialModel) error {
	var isImmutable bool
	err := r.pool.QueryRow(ctx, `SELECT is_immutable FROM spatial_models WHERE id = $1`, m.ID).Scan(&isImmutable)
	if err != nil {
		return err
	}
	if isImmutable {
		return domain.ErrModelImmutable
	}

	bboxJSON, _ := json.Marshal(m.BoundingBox)
	coordJSON, _ := json.Marshal(m.CoordinateFrame)
	query := `
		UPDATE spatial_models
		SET title = $1, description = $2, bounding_box = $3, coordinate_frame = $4,
		    total_vertices = $5, total_faces = $6, point_density_sqm = $7,
		    precision_deviation_cm = $8, is_active_version = $9, updated_at = NOW()
		WHERE id = $10
	`
	_, err = r.pool.Exec(ctx, query,
		m.Title, m.Description, bboxJSON, coordJSON,
		m.TotalVertices, m.TotalFaces, m.PointDensitySQM,
		m.PrecisionDeviationCM, m.IsActiveVersion, m.ID,
	)
	return err
}

func (r *ModelRepo) CreateArtifact(ctx context.Context, a *domain.ModelArtifact) error {
	query := `
		INSERT INTO model_artifacts (id, model_id, artifact_type, lod_level, file_format, file_size_bytes, file_url, sha256_hash, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
	`
	if a.ID == uuid.Nil {
		a.ID = uuid.New()
	}
	if a.CreatedAt.IsZero() {
		a.CreatedAt = time.Now().UTC()
	}

	_, err := r.pool.Exec(ctx, query, a.ID, a.ModelID, a.ArtifactType, a.LODLevel, a.FileFormat, a.FileSizeBytes, a.FileURL, a.SHA256Hash, a.CreatedAt)
	return err
}

func (r *ModelRepo) ListArtifactsByModel(ctx context.Context, modelID uuid.UUID) ([]*domain.ModelArtifact, error) {
	query := `
		SELECT id, model_id, artifact_type, lod_level, file_format, file_size_bytes, file_url, sha256_hash, created_at
		FROM model_artifacts WHERE model_id = $1 ORDER BY lod_level ASC
	`
	rows, err := r.pool.Query(ctx, query, modelID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.ModelArtifact
	for rows.Next() {
		a := &domain.ModelArtifact{}
		if err := rows.Scan(&a.ID, &a.ModelID, &a.ArtifactType, &a.LODLevel, &a.FileFormat, &a.FileSizeBytes, &a.FileURL, &a.SHA256Hash, &a.CreatedAt); err != nil {
			return nil, err
		}
		list = append(list, a)
	}
	return list, nil
}

// ==========================================
// 5. POI & Search Repository
// ==========================================

type POIRepo struct {
	pool *pgxpool.Pool
}

func NewPOIRepo(pool *pgxpool.Pool) *POIRepo {
	return &POIRepo{pool: pool}
}

func (r *POIRepo) Create(ctx context.Context, p *domain.SpatialPOI) error {
	metaJSON, _ := json.Marshal(p.CustomMetadata)
	attachJSON, _ := json.Marshal(p.Attachments)
	viewJSON, _ := json.Marshal(p.CameraViewpoint)

	query := `
		INSERT INTO spatial_pois (
			id, project_id, level_id, section_id, title, description, category,
			pos_x, pos_y, pos_z, normal_x, normal_y, normal_z, icon_key, color_hex,
			tags, custom_metadata, attachments, camera_viewpoint, created_by,
			created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
			$16, $17, $18, $19, $20, $21, $22
		)
	`
	now := time.Now().UTC()
	p.CreatedAt = now
	p.UpdatedAt = now

	_, err := r.pool.Exec(ctx, query,
		p.ID, p.ProjectID, p.LevelID, p.SectionID, p.Title, p.Description, string(p.Category),
		p.PosX, p.PosY, p.PosZ, p.NormalX, p.NormalY, p.NormalZ, p.IconKey, p.ColorHex,
		p.Tags, metaJSON, attachJSON, viewJSON, p.CreatedBy, p.CreatedAt, p.UpdatedAt,
	)
	return err
}

func (r *POIRepo) GetByID(ctx context.Context, id uuid.UUID) (*domain.SpatialPOI, error) {
	query := `
		SELECT 
			id, project_id, level_id, section_id, title, description, category,
			pos_x, pos_y, pos_z, normal_x, normal_y, normal_z, icon_key, color_hex,
			tags, custom_metadata, attachments, camera_viewpoint, created_by,
			created_at, updated_at
		FROM spatial_pois WHERE id = $1
	`
	p := &domain.SpatialPOI{}
	var catStr string
	var metaBytes, attachBytes, viewBytes []byte

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&p.ID, &p.ProjectID, &p.LevelID, &p.SectionID, &p.Title, &p.Description, &catStr,
		&p.PosX, &p.PosY, &p.PosZ, &p.NormalX, &p.NormalY, &p.NormalZ, &p.IconKey, &p.ColorHex,
		&p.Tags, &metaBytes, &attachBytes, &viewBytes, &p.CreatedBy, &p.CreatedAt, &p.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("poi not found")
		}
		return nil, err
	}

	p.Category = domain.POICategory(catStr)
	if len(metaBytes) > 0 {
		_ = json.Unmarshal(metaBytes, &p.CustomMetadata)
	}
	if len(attachBytes) > 0 {
		_ = json.Unmarshal(attachBytes, &p.Attachments)
	}
	if len(viewBytes) > 0 {
		_ = json.Unmarshal(viewBytes, &p.CameraViewpoint)
	}
	return p, nil
}

func (r *POIRepo) ListByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.SpatialPOI, error) {
	query := `
		SELECT 
			id, project_id, level_id, section_id, title, description, category,
			pos_x, pos_y, pos_z, normal_x, normal_y, normal_z, icon_key, color_hex,
			tags, custom_metadata, attachments, camera_viewpoint, created_by,
			created_at, updated_at
		FROM spatial_pois WHERE project_id = $1 ORDER BY title ASC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.SpatialPOI
	for rows.Next() {
		p := &domain.SpatialPOI{}
		var catStr string
		var metaBytes, attachBytes, viewBytes []byte

		if err := rows.Scan(
			&p.ID, &p.ProjectID, &p.LevelID, &p.SectionID, &p.Title, &p.Description, &catStr,
			&p.PosX, &p.PosY, &p.PosZ, &p.NormalX, &p.NormalY, &p.NormalZ, &p.IconKey, &p.ColorHex,
			&p.Tags, &metaBytes, &attachBytes, &viewBytes, &p.CreatedBy, &p.CreatedAt, &p.UpdatedAt,
		); err != nil {
			return nil, err
		}
		p.Category = domain.POICategory(catStr)
		if len(metaBytes) > 0 {
			_ = json.Unmarshal(metaBytes, &p.CustomMetadata)
		}
		if len(attachBytes) > 0 {
			_ = json.Unmarshal(attachBytes, &p.Attachments)
		}
		if len(viewBytes) > 0 {
			_ = json.Unmarshal(viewBytes, &p.CameraViewpoint)
		}
		list = append(list, p)
	}
	return list, nil
}

func (r *POIRepo) Update(ctx context.Context, p *domain.SpatialPOI) error {
	metaJSON, _ := json.Marshal(p.CustomMetadata)
	attachJSON, _ := json.Marshal(p.Attachments)
	viewJSON, _ := json.Marshal(p.CameraViewpoint)

	query := `
		UPDATE spatial_pois SET
			title = $2,
			description = $3,
			category = $4,
			pos_x = $5,
			pos_y = $6,
			pos_z = $7,
			icon_key = $8,
			color_hex = $9,
			tags = $10,
			custom_metadata = $11,
			attachments = $12,
			camera_viewpoint = $13,
			updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.pool.Exec(ctx, query,
		p.ID, p.Title, p.Description, string(p.Category),
		p.PosX, p.PosY, p.PosZ, p.IconKey, p.ColorHex,
		p.Tags, metaJSON, attachJSON, viewJSON,
	)
	return err
}

func (r *POIRepo) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM spatial_pois WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *POIRepo) Search(ctx context.Context, q domain.SpatialSearchQuery) ([]*domain.SearchResultItem, error) {
	searchTerm := "%" + q.Query + "%"
	query := `
		SELECT 
			p.id, 'poi' as result_type, p.title, COALESCE(p.description, '') as description,
			p.category, p.pos_x, p.pos_y, p.pos_z,
			COALESCE(l.level_name, '') as level_name,
			COALESCE(s.name, '') as section_name
		FROM spatial_pois p
		LEFT JOIN spatial_levels l ON p.level_id = l.id
		LEFT JOIN spatial_sections s ON p.section_id = s.id
		WHERE p.project_id = $1
		  AND (p.title ILIKE $2 OR p.description ILIKE $2 OR array_to_string(p.tags, ' ') ILIKE $2)
	`
	rows, err := r.pool.Query(ctx, query, q.ProjectID, searchTerm)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []*domain.SearchResultItem
	for rows.Next() {
		item := &domain.SearchResultItem{
			Position: make(map[string]float64),
		}
		var px, py, pz float64
		if err := rows.Scan(
			&item.ID, &item.ResultType, &item.Title, &item.Description, &item.Category,
			&px, &py, &pz, &item.LevelName, &item.SectionName,
		); err != nil {
			return nil, err
		}
		item.Position["x"] = px
		item.Position["y"] = py
		item.Position["z"] = pz
		item.Score = 1.0

		// Distance calculation if reference position provided
		if q.CenterPosX != nil && q.CenterPosY != nil && q.CenterPosZ != nil {
			dx := px - *q.CenterPosX
			dy := py - *q.CenterPosY
			dz := pz - *q.CenterPosZ
			dist := (dx*dx + dy*dy + dz*dz)
			item.DistanceM = &dist
		}

		results = append(results, item)
	}

	return results, nil
}

// ==========================================
// 6. Navigation Repository
// ==========================================

type NavigationRepo struct {
	pool *pgxpool.Pool
}

func NewNavigationRepo(pool *pgxpool.Pool) *NavigationRepo {
	return &NavigationRepo{pool: pool}
}

func (r *NavigationRepo) CreateNode(ctx context.Context, n *domain.NavNode) error {
	query := `
		INSERT INTO nav_nodes (id, project_id, level_id, section_id, node_type, pos_x, pos_y, pos_z, is_wheelchair_accessible, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`
	if n.ID == uuid.Nil {
		n.ID = uuid.New()
	}
	if n.CreatedAt.IsZero() {
		n.CreatedAt = time.Now().UTC()
	}

	_, err := r.pool.Exec(ctx, query, n.ID, n.ProjectID, n.LevelID, n.SectionID, string(n.NodeType), n.PosX, n.PosY, n.PosZ, n.IsWheelchairAccessible, n.CreatedAt)
	return err
}

func (r *NavigationRepo) GetNodeByID(ctx context.Context, id uuid.UUID) (*domain.NavNode, error) {
	query := `
		SELECT id, project_id, level_id, section_id, node_type, pos_x, pos_y, pos_z, is_wheelchair_accessible, created_at
		FROM nav_nodes WHERE id = $1
	`
	n := &domain.NavNode{}
	var typeStr string
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&n.ID, &n.ProjectID, &n.LevelID, &n.SectionID, &typeStr, &n.PosX, &n.PosY, &n.PosZ, &n.IsWheelchairAccessible, &n.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, errors.New("nav node not found")
		}
		return nil, err
	}
	n.NodeType = domain.NavNodeType(typeStr)
	return n, nil
}

func (r *NavigationRepo) ListNodesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavNode, error) {
	query := `
		SELECT id, project_id, level_id, section_id, node_type, pos_x, pos_y, pos_z, is_wheelchair_accessible, created_at
		FROM nav_nodes WHERE project_id = $1
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var nodes []*domain.NavNode
	for rows.Next() {
		n := &domain.NavNode{}
		var typeStr string
		if err := rows.Scan(
			&n.ID, &n.ProjectID, &n.LevelID, &n.SectionID, &typeStr, &n.PosX, &n.PosY, &n.PosZ, &n.IsWheelchairAccessible, &n.CreatedAt,
		); err != nil {
			return nil, err
		}
		n.NodeType = domain.NavNodeType(typeStr)
		nodes = append(nodes, n)
	}
	return nodes, nil
}

func (r *NavigationRepo) CreateEdge(ctx context.Context, e *domain.NavEdge) error {
	query := `
		INSERT INTO nav_edges (id, project_id, from_node_id, to_node_id, edge_type, distance_meters, is_bidirectional, is_wheelchair_accessible, weight_modifier, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		ON CONFLICT (from_node_id, to_node_id) DO UPDATE SET
			distance_meters = EXCLUDED.distance_meters,
			is_wheelchair_accessible = EXCLUDED.is_wheelchair_accessible,
			weight_modifier = EXCLUDED.weight_modifier
	`
	if e.ID == uuid.Nil {
		e.ID = uuid.New()
	}
	if e.CreatedAt.IsZero() {
		e.CreatedAt = time.Now().UTC()
	}

	_, err := r.pool.Exec(ctx, query,
		e.ID, e.ProjectID, e.FromNodeID, e.ToNodeID, string(e.EdgeType),
		e.DistanceMeters, e.IsBidirectional, e.IsWheelchairAccessible, e.WeightModifier, e.CreatedAt,
	)
	return err
}

func (r *NavigationRepo) ListEdgesByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.NavEdge, error) {
	query := `
		SELECT id, project_id, from_node_id, to_node_id, edge_type, distance_meters, is_bidirectional, is_wheelchair_accessible, weight_modifier, created_at
		FROM nav_edges WHERE project_id = $1
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var edges []*domain.NavEdge
	for rows.Next() {
		e := &domain.NavEdge{}
		var typeStr string
		if err := rows.Scan(
			&e.ID, &e.ProjectID, &e.FromNodeID, &e.ToNodeID, &typeStr,
			&e.DistanceMeters, &e.IsBidirectional, &e.IsWheelchairAccessible, &e.WeightModifier, &e.CreatedAt,
		); err != nil {
			return nil, err
		}
		e.EdgeType = domain.NavEdgeType(typeStr)
		edges = append(edges, e)
	}
	return edges, nil
}

func (r *NavigationRepo) DeleteNode(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM nav_nodes WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *NavigationRepo) DeleteEdge(ctx context.Context, fromID, toID uuid.UUID) error {
	query := `DELETE FROM nav_edges WHERE from_node_id = $1 AND to_node_id = $2`
	_, err := r.pool.Exec(ctx, query, fromID, toID)
	return err
}

// ==========================================
// 7. Viewer Repository
// ==========================================

type ViewerRepo struct {
	pool *pgxpool.Pool
}

func NewViewerRepo(pool *pgxpool.Pool) *ViewerRepo {
	return &ViewerRepo{pool: pool}
}

func (r *ViewerRepo) CreateBookmark(ctx context.Context, b *domain.ViewerBookmark) error {
	posJSON, _ := json.Marshal(b.CameraPosition)
	targetJSON, _ := json.Marshal(b.CameraTarget)
	layersJSON, _ := json.Marshal(b.VisibleLayers)

	query := `
		INSERT INTO viewer_bookmarks (id, project_id, user_id, title, camera_position, camera_target, camera_fov, visible_layers, is_shared, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`
	if b.ID == uuid.Nil {
		b.ID = uuid.New()
	}
	if b.CreatedAt.IsZero() {
		b.CreatedAt = time.Now().UTC()
	}

	_, err := r.pool.Exec(ctx, query,
		b.ID, b.ProjectID, b.UserID, b.Title, posJSON, targetJSON, b.CameraFOV, layersJSON, b.IsShared, b.CreatedAt,
	)
	return err
}

func (r *ViewerRepo) ListBookmarksByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ViewerBookmark, error) {
	query := `
		SELECT id, project_id, user_id, title, camera_position, camera_target, camera_fov, visible_layers, is_shared, created_at
		FROM viewer_bookmarks WHERE project_id = $1 ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.ViewerBookmark
	for rows.Next() {
		b := &domain.ViewerBookmark{}
		var posBytes, targetBytes, layersBytes []byte
		if err := rows.Scan(
			&b.ID, &b.ProjectID, &b.UserID, &b.Title, &posBytes, &targetBytes, &b.CameraFOV, &layersBytes, &b.IsShared, &b.CreatedAt,
		); err != nil {
			return nil, err
		}
		if len(posBytes) > 0 {
			_ = json.Unmarshal(posBytes, &b.CameraPosition)
		}
		if len(targetBytes) > 0 {
			_ = json.Unmarshal(targetBytes, &b.CameraTarget)
		}
		if len(layersBytes) > 0 {
			_ = json.Unmarshal(layersBytes, &b.VisibleLayers)
		}
		list = append(list, b)
	}
	return list, nil
}

func (r *ViewerRepo) DeleteBookmark(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM viewer_bookmarks WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *ViewerRepo) CreateAnnotation(ctx context.Context, a *domain.ViewerAnnotation) error {
	pointsJSON, _ := json.Marshal(a.Points3D)
	query := `
		INSERT INTO viewer_annotations (id, project_id, user_id, annotation_type, points_3d, calculated_value, unit, label, color_hex, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`
	if a.ID == uuid.Nil {
		a.ID = uuid.New()
	}
	if a.CreatedAt.IsZero() {
		a.CreatedAt = time.Now().UTC()
	}

	_, err := r.pool.Exec(ctx, query,
		a.ID, a.ProjectID, a.UserID, a.AnnotationType, pointsJSON, a.CalculatedValue, a.Unit, a.Label, a.ColorHex, a.CreatedAt,
	)
	return err
}

func (r *ViewerRepo) ListAnnotationsByProject(ctx context.Context, projectID uuid.UUID) ([]*domain.ViewerAnnotation, error) {
	query := `
		SELECT id, project_id, user_id, annotation_type, points_3d, calculated_value, unit, label, color_hex, created_at
		FROM viewer_annotations WHERE project_id = $1 ORDER BY created_at DESC
	`
	rows, err := r.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.ViewerAnnotation
	for rows.Next() {
		a := &domain.ViewerAnnotation{}
		var pointsBytes []byte
		if err := rows.Scan(
			&a.ID, &a.ProjectID, &a.UserID, &a.AnnotationType, &pointsBytes, &a.CalculatedValue, &a.Unit, &a.Label, &a.ColorHex, &a.CreatedAt,
		); err != nil {
			return nil, err
		}
		if len(pointsBytes) > 0 {
			_ = json.Unmarshal(pointsBytes, &a.Points3D)
		}
		list = append(list, a)
	}
	return list, nil
}

func (r *ViewerRepo) DeleteAnnotation(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM viewer_annotations WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

// ===========================================================================
// PostGIS Spatial Extensions — NavigationRepo
// ===========================================================================

// NearestNode finds the closest nav_node to a 3D position using the PostGIS
// KNN GiST operator (<->). This is O(log n) via the spatial index, replacing
// the O(n) in-memory linear scan previously used in navigation_service.go.
func (r *NavigationRepo) NearestNode(
	ctx context.Context,
	projectID uuid.UUID,
	pos geo.Point3D,
	wheelchairOnly bool,
) (*domain.NavNode, error) {
	query := `
		SELECT
			id, project_id, level_id, section_id, node_type,
			pos_x, pos_y, pos_z,
			is_wheelchair_accessible, created_at
		FROM nav_nodes
		WHERE project_id = $1
		  AND geom IS NOT NULL
		  AND ($2 = FALSE OR is_wheelchair_accessible = TRUE)
		ORDER BY geom <-> ST_SetSRID(ST_MakePoint($3, $4, $5), 0)
		LIMIT 1
	`
	n := &domain.NavNode{}
	var nodeTypeStr string
	err := r.pool.QueryRow(ctx, query,
		projectID,
		wheelchairOnly,
		pos.X, pos.Y, pos.Z,
	).Scan(
		&n.ID, &n.ProjectID, &n.LevelID, &n.SectionID, &nodeTypeStr,
		&n.PosX, &n.PosY, &n.PosZ,
		&n.IsWheelchairAccessible, &n.CreatedAt,
	)
	if err != nil {
		return nil, err
	}
	n.NodeType = domain.NavNodeType(nodeTypeStr)
	return n, nil
}

// ===========================================================================
// PostGIS Spatial Extensions — POIRepo
// ===========================================================================

// POIsWithinRadius finds all POIs within a 3D Euclidean radius of a query
// point, using the vastu_pois_within_radius() PostgreSQL function which is
// backed by a GiST spatial index on spatial_pois.geom.
func (r *POIRepo) POIsWithinRadius(
	ctx context.Context,
	projectID uuid.UUID,
	center geo.Point3D,
	radiusM float64,
) ([]*domain.SearchResultItem, error) {
	query := `
		SELECT id, title, category, pos_x, pos_y, pos_z, distance_m
		FROM vastu_pois_within_radius($1, $2, $3, $4, $5)
	`
	rows, err := r.pool.Query(ctx, query,
		projectID,
		center.X, center.Y, center.Z,
		radiusM,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []*domain.SearchResultItem
	for rows.Next() {
		var (
			id         uuid.UUID
			title      string
			category   string
			posX, posY, posZ float64
			distM      float64
		)
		if err := rows.Scan(&id, &title, &category, &posX, &posY, &posZ, &distM); err != nil {
			return nil, err
		}
		results = append(results, &domain.SearchResultItem{
			ID:         id,
			ResultType: "poi",
			Title:      title,
			Category:   category,
			Position: map[string]float64{
				"x": posX, "y": posY, "z": posZ,
			},
			DistanceM: &distM,
			Score:     1.0 / (1.0 + distM), // proximity score
		})
	}
	return results, rows.Err()
}

