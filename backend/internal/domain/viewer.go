package domain

import (
	"time"

	"github.com/google/uuid"
)

type ViewerBookmark struct {
	ID            uuid.UUID              `json:"id"`
	ProjectID     uuid.UUID              `json:"project_id"`
	UserID        *uuid.UUID             `json:"user_id,omitempty"`
	Title         string                 `json:"title"`
	CameraPosition map[string]float64    `json:"camera_position"` // x, y, z
	CameraTarget   map[string]float64    `json:"camera_target"`   // x, y, z
	CameraFOV      float64                `json:"camera_fov"`
	VisibleLayers  []string               `json:"visible_layers"`
	IsShared       bool                   `json:"is_shared"`
	CreatedAt      time.Time              `json:"created_at"`
}

type ViewerAnnotation struct {
	ID              uuid.UUID              `json:"id"`
	ProjectID       uuid.UUID              `json:"project_id"`
	UserID          *uuid.UUID             `json:"user_id,omitempty"`
	AnnotationType  string                 `json:"annotation_type"` // 'distance', 'area', 'volume', 'text_note', 'angle'
	Points3D        [][]float64            `json:"points_3d"`
	CalculatedValue *float64               `json:"calculated_value,omitempty"`
	Unit            string                 `json:"unit"`
	Label           *string                `json:"label,omitempty"`
	ColorHex        string                 `json:"color_hex"`
	CreatedAt       time.Time              `json:"created_at"`
}

type CreateBookmarkInput struct {
	ProjectID      uuid.UUID          `json:"project_id"`
	Title          string             `json:"title"`
	CameraPosition map[string]float64 `json:"camera_position"`
	CameraTarget   map[string]float64 `json:"camera_target"`
	CameraFOV      *float64           `json:"camera_fov,omitempty"`
	VisibleLayers  []string           `json:"visible_layers,omitempty"`
	IsShared       *bool              `json:"is_shared,omitempty"`
}

type CreateAnnotationInput struct {
	ProjectID       uuid.UUID   `json:"project_id"`
	AnnotationType  string      `json:"annotation_type"`
	Points3D        [][]float64 `json:"points_3d"`
	CalculatedValue *float64    `json:"calculated_value,omitempty"`
	Unit            *string     `json:"unit,omitempty"`
	Label           *string     `json:"label,omitempty"`
	ColorHex        *string     `json:"color_hex,omitempty"`
}
