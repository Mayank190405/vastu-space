package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"vastu/backend/internal/domain"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

type RescanService struct {
	pool *pgxpool.Pool
}

func NewRescanService(pool *pgxpool.Pool) *RescanService {
	return &RescanService{pool: pool}
}

type CreateRescanRequestInput struct {
	ProjectID          uuid.UUID  `json:"project_id"`
	QualityReportID    *uuid.UUID `json:"quality_report_id,omitempty"`
	CellID             *uuid.UUID `json:"cell_id,omitempty"`
	AssignedOperatorID *uuid.UUID `json:"assigned_operator_id,omitempty"`
	AreaName           string     `json:"area_name"`
	FailureReason      string     `json:"failure_reason"`
	MobileInstruction  string     `json:"mobile_instruction"`
	TargetCenterX      float64    `json:"target_center_x"`
	TargetCenterY      float64    `json:"target_center_y"`
	TargetCenterZ      float64    `json:"target_center_z"`
	TargetRadiusM      float64    `json:"target_radius_m"`
}

func (s *RescanService) CreateRequest(ctx context.Context, input CreateRescanRequestInput) (*domain.RescanRequest, error) {
	if input.ProjectID == uuid.Nil {
		return nil, errors.New("project_id is required")
	}
	if input.AreaName == "" {
		return nil, errors.New("area_name is required")
	}
	if input.TargetRadiusM <= 0 {
		input.TargetRadiusM = 2.50
	}

	req := &domain.RescanRequest{
		ID:                 uuid.New(),
		ProjectID:          input.ProjectID,
		QualityReportID:    input.QualityReportID,
		CellID:             input.CellID,
		AssignedOperatorID: input.AssignedOperatorID,
		AreaName:           input.AreaName,
		FailureReason:      input.FailureReason,
		MobileInstruction:  input.MobileInstruction,
		TargetCenterX:      input.TargetCenterX,
		TargetCenterY:      input.TargetCenterY,
		TargetCenterZ:      input.TargetCenterZ,
		TargetRadiusM:      input.TargetRadiusM,
		Status:             "pending",
		CreatedAt:          time.Now().UTC(),
		UpdatedAt:          time.Now().UTC(),
	}

	query := `
		INSERT INTO rescan_requests (
			id, project_id, quality_report_id, cell_id, assigned_operator_id,
			area_name, failure_reason, mobile_instruction,
			target_center_x, target_center_y, target_center_z, target_radius_m,
			status, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
	`
	_, err := s.pool.Exec(ctx, query,
		req.ID, req.ProjectID, req.QualityReportID, req.CellID, req.AssignedOperatorID,
		req.AreaName, req.FailureReason, req.MobileInstruction,
		req.TargetCenterX, req.TargetCenterY, req.TargetCenterZ, req.TargetRadiusM,
		req.Status, req.CreatedAt, req.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create rescan request: %w", err)
	}

	return req, nil
}

func (s *RescanService) ListPendingRequests(ctx context.Context, projectID uuid.UUID) ([]*domain.RescanRequest, error) {
	query := `
		SELECT id, project_id, quality_report_id, cell_id, assigned_operator_id,
		       area_name, failure_reason, mobile_instruction,
		       target_center_x, target_center_y, target_center_z, target_radius_m,
		       status, rescan_capture_id, created_at, updated_at
		FROM rescan_requests
		WHERE project_id = $1 AND status IN ('pending', 'assigned', 'capturing')
		ORDER BY created_at DESC
	`
	rows, err := s.pool.Query(ctx, query, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*domain.RescanRequest
	for rows.Next() {
		var req domain.RescanRequest
		err := rows.Scan(
			&req.ID, &req.ProjectID, &req.QualityReportID, &req.CellID, &req.AssignedOperatorID,
			&req.AreaName, &req.FailureReason, &req.MobileInstruction,
			&req.TargetCenterX, &req.TargetCenterY, &req.TargetCenterZ, &req.TargetRadiusM,
			&req.Status, &req.RescanCaptureID, &req.CreatedAt, &req.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}
		list = append(list, &req)
	}

	return list, nil
}

func (s *RescanService) UpdateStatus(ctx context.Context, requestID uuid.UUID, status string, captureID *uuid.UUID) error {
	query := `
		UPDATE rescan_requests
		SET status = $1, rescan_capture_id = COALESCE($2, rescan_capture_id), updated_at = NOW()
		WHERE id = $3
	`
	tag, err := s.pool.Exec(ctx, query, status, captureID, requestID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return errors.New("rescan request not found")
	}
	return nil
}
