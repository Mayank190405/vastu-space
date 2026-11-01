package domain

import (
	"time"

	"github.com/google/uuid"
)

type AlignmentStatus string

const (
	AlignmentStatusPending           AlignmentStatus = "PENDING"
	AlignmentStatusAligned           AlignmentStatus = "ALIGNED"
	AlignmentStatusNeedsManualReview AlignmentStatus = "NEEDS_MANUAL_REVIEW"
	AlignmentStatusFailed            AlignmentStatus = "FAILED"
)

type RoomAlignmentRecord struct {
	ID                 uuid.UUID       `json:"id"`
	ProjectID          uuid.UUID       `json:"project_id"`
	SourceRoomID       uuid.UUID       `json:"source_room_id"`
	TargetRoomID       uuid.UUID       `json:"target_room_id"`
	DoorwayID          string          `json:"doorway_id"`
	Status             AlignmentStatus `json:"status"`
	TransformMatrix4x4 [][]float64     `json:"transform_matrix_4x4"`
	RMSEMillimeters    float64         `json:"rmse_mm"`
	Confidence         float64         `json:"confidence"`
	InlierRatio        float64         `json:"inlier_ratio"`
	ReviewedBy         *string         `json:"reviewed_by,omitempty"`
	CreatedAt          time.Time       `json:"created_at"`
	UpdatedAt          time.Time       `json:"updated_at"`
}

type RoomConnectionEdge struct {
	DoorwayID    string    `json:"doorway_id"`
	SourceRoomID uuid.UUID `json:"source_room_id"`
	TargetRoomID uuid.UUID `json:"target_room_id"`
	WidthMeters  float64   `json:"width_m"`
	HeightMeters float64   `json:"height_m"`
	Center3D     []float64 `json:"center_3d"`
	Confidence   float64   `json:"confidence"`
	IsOpen       bool      `json:"is_open"`
}

type RoomConnectionGraphResponse struct {
	ProjectID           uuid.UUID            `json:"project_id"`
	RoomCount           int                  `json:"room_count"`
	ConnectionCount     int                  `json:"connection_count"`
	ConnectedComponents int                  `json:"connected_components"`
	Rooms               []*RoomWithHierarchy `json:"rooms"`
	Doorways            []RoomConnectionEdge `json:"doorways"`
}

type UnifiedSceneAssets struct {
	ArchitectureOBJ   string  `json:"architecture_obj"`
	CollisionGeometry string  `json:"collision_geometry"`
	Navmesh           string  `json:"navmesh"`
	ConnectionGraph   string  `json:"connection_graph"`
	SplatsSPZ         *string `json:"splats_spz,omitempty"`
}

type DefaultSpawnLocation struct {
	RoomID      string    `json:"room_id"`
	Position3D  []float64 `json:"position_3d"`
	EyeHeightM  float64   `json:"eye_height_m"`
}

type UnifiedSceneManifest struct {
	Version        string                `json:"version"`
	ProjectID      uuid.UUID             `json:"project_id"`
	ProjectName    string                `json:"project_name"`
	AssembledAt    time.Time             `json:"assembled_at"`
	TotalAreaSqm   float64               `json:"total_area_sqm"`
	RoomCount      int                   `json:"room_count"`
	Floors         []int                 `json:"floors"`
	Assets         UnifiedSceneAssets    `json:"assets"`
	Rooms          []*RoomWithHierarchy  `json:"rooms"`
	DefaultSpawn   DefaultSpawnLocation  `json:"default_spawn"`
}

type AlignRoomsInput struct {
	ProjectID    uuid.UUID  `json:"project_id"`
	SourceRoomID uuid.UUID  `json:"source_room_id"`
	TargetRoomID uuid.UUID  `json:"target_room_id"`
	DoorwayID    string     `json:"doorway_id"`
}

type AssembleSpaceInput struct {
	ProjectID    uuid.UUID  `json:"project_id"`
	RootRoomID   *uuid.UUID `json:"root_room_id,omitempty"`
}

type AssembleSpaceResponse struct {
	Status      string                `json:"status"`
	ManifestURL string                `json:"manifest_url"`
	Manifest    UnifiedSceneManifest  `json:"manifest"`
}

