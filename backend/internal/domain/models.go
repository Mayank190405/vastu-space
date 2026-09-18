package domain

import (
	"time"

	"github.com/google/uuid"
)

type SpatialModel struct {
	ID                   uuid.UUID              `json:"id"`
	ProjectID            uuid.UUID              `json:"project_id"`
	LevelID              *uuid.UUID             `json:"level_id,omitempty"`
	SectionID            *uuid.UUID             `json:"section_id,omitempty"`
	Version              string                 `json:"version"`
	Title                string                 `json:"title"`
	Description          *string                `json:"description,omitempty"`
	BoundingBox          map[string]interface{} `json:"bounding_box,omitempty"`
	CoordinateFrame      map[string]interface{} `json:"coordinate_frame,omitempty"`
	TotalVertices        int64                  `json:"total_vertices"`
	TotalFaces           int64                  `json:"total_faces"`
	PointDensitySQM      float64                `json:"point_density_sqm"`
	PrecisionDeviationCM float64                `json:"precision_deviation_cm"`
	IsActiveVersion      bool                   `json:"is_active_version"`
	ParentModelID        *uuid.UUID             `json:"parent_model_id,omitempty"`
	IsImmutable          bool                   `json:"is_immutable"`
	QualityReportID      *uuid.UUID             `json:"quality_report_id,omitempty"`
	SourceCaptureID      *uuid.UUID             `json:"source_capture_id,omitempty"`
	PublishedAt          *time.Time             `json:"published_at,omitempty"`
	LineageDepth         int                    `json:"lineage_depth"`
	CreatedBy            *uuid.UUID             `json:"created_by,omitempty"`
	CreatedAt            time.Time              `json:"created_at"`
	UpdatedAt            time.Time              `json:"updated_at"`
	Artifacts            []*ModelArtifact       `json:"artifacts,omitempty"`
}

type QualityReport struct {
	ID                   uuid.UUID              `json:"id"`
	ProjectID            uuid.UUID              `json:"project_id"`
	JobID                *uuid.UUID             `json:"job_id,omitempty"`
	ModelID              *uuid.UUID             `json:"model_id,omitempty"`
	Status               string                 `json:"status"` // 'PASS', 'FAIL', 'WARNING'
	OverallScore         float64                `json:"overall_score"`
	GeometryScore        float64                `json:"geometry_score"`
	TrackingScore        float64                `json:"tracking_score"`
	CoverageScore        float64                `json:"coverage_score"`
	TextureScore         float64                `json:"texture_score"`
	SemanticScore        float64                `json:"semantic_score"`
	CellConsistencyScore float64                `json:"cell_consistency_score"`
	NavigationScore      float64                `json:"navigation_score"`
	LowConfidenceCells   map[string]interface{} `json:"low_confidence_cells,omitempty"`
	FailureReasons       []string               `json:"failure_reasons,omitempty"`
	Recommendations      *string                `json:"recommendations,omitempty"`
	CreatedAt            time.Time              `json:"created_at"`
}

type RescanRequest struct {
	ID                 uuid.UUID  `json:"id"`
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
	Status             string     `json:"status"` // 'pending', 'assigned', 'capturing', 'uploaded', 'fused', 'ignored'
	RescanCaptureID    *uuid.UUID `json:"rescan_capture_id,omitempty"`
	CreatedAt          time.Time  `json:"created_at"`
	UpdatedAt          time.Time  `json:"updated_at"`
}

type ModelArtifact struct {
	ID            uuid.UUID `json:"id"`
	ModelID       uuid.UUID `json:"model_id"`
	ArtifactType  string    `json:"artifact_type"` // 'point_cloud_ply', 'mesh_gltf', 'gaussian_splat', 'lod0', etc.
	LODLevel      int       `json:"lod_level"`
	FileFormat    string    `json:"file_format"`
	FileSizeBytes int64     `json:"file_size_bytes"`
	FileURL       string    `json:"file_url"`
	SHA256Hash    *string   `json:"sha256_hash,omitempty"`
	CreatedAt     time.Time `json:"created_at"`
}

type CreateModelInput struct {
	ProjectID            uuid.UUID              `json:"project_id"`
	LevelID              *uuid.UUID             `json:"level_id,omitempty"`
	SectionID            *uuid.UUID             `json:"section_id,omitempty"`
	Version              string                 `json:"version"`
	Title                string                 `json:"title"`
	Description          *string                `json:"description,omitempty"`
	BoundingBox          map[string]interface{} `json:"bounding_box,omitempty"`
	CoordinateFrame      map[string]interface{} `json:"coordinate_frame,omitempty"`
	TotalVertices        int64                  `json:"total_vertices"`
	TotalFaces           int64                  `json:"total_faces"`
	PointDensitySQM      float64                `json:"point_density_sqm"`
	PrecisionDeviationCM float64                `json:"precision_deviation_cm"`
	Artifacts            []CreateArtifactInput  `json:"artifacts,omitempty"`
}

type CreateArtifactInput struct {
	ArtifactType  string  `json:"artifact_type"`
	LODLevel      int     `json:"lod_level"`
	FileFormat    string  `json:"file_format"`
	FileSizeBytes int64   `json:"file_size_bytes"`
	FileURL       string  `json:"file_url"`
	SHA256Hash    *string `json:"sha256_hash,omitempty"`
}
