package domain

import (
	"time"

	"github.com/google/uuid"
)

type POICategory string

const (
	POICategoryRoomLabel     POICategory = "room_label"
	POICategoryAsset         POICategory = "asset"
	POICategoryEquipment     POICategory = "equipment"
	POICategoryEmergencyExit POICategory = "emergency_exit"
	POICategoryRestroom      POICategory = "restroom"
	POICategoryElevator      POICategory = "elevator"
	POICategorySensor        POICategory = "sensor"
	POICategoryStaircase     POICategory = "staircase"
	POICategoryStructural    POICategory = "structural"
	POICategoryCustom        POICategory = "custom"
)

type SpatialPOI struct {
	ID              uuid.UUID              `json:"id"`
	ProjectID       uuid.UUID              `json:"project_id"`
	LevelID         *uuid.UUID             `json:"level_id,omitempty"`
	SectionID       *uuid.UUID             `json:"section_id,omitempty"`
	Title           string                 `json:"title"`
	Description     *string                `json:"description,omitempty"`
	Category        POICategory            `json:"category"`
	PosX            float64                `json:"pos_x"`
	PosY            float64                `json:"pos_y"`
	PosZ            float64                `json:"pos_z"`
	NormalX         float64                `json:"normal_x"`
	NormalY         float64                `json:"normal_y"`
	NormalZ         float64                `json:"normal_z"`
	IconKey         string                 `json:"icon_key"`
	ColorHex        string                 `json:"color_hex"`
	Tags            []string               `json:"tags"`
	CustomMetadata  map[string]interface{} `json:"custom_metadata"`
	Attachments     []interface{}          `json:"attachments"`
	CameraViewpoint map[string]interface{} `json:"camera_viewpoint,omitempty"`
	CreatedBy       *uuid.UUID             `json:"created_by,omitempty"`
	CreatedAt       time.Time              `json:"created_at"`
	UpdatedAt       time.Time              `json:"updated_at"`
}

type CreatePOIInput struct {
	ProjectID       uuid.UUID              `json:"project_id"`
	LevelID         *uuid.UUID             `json:"level_id,omitempty"`
	SectionID       *uuid.UUID             `json:"section_id,omitempty"`
	Title           string                 `json:"title"`
	Description     *string                `json:"description,omitempty"`
	Category        POICategory            `json:"category"`
	PosX            float64                `json:"pos_x"`
	PosY            float64                `json:"pos_y"`
	PosZ            float64                `json:"pos_z"`
	NormalX         *float64               `json:"normal_x,omitempty"`
	NormalY         *float64               `json:"normal_y,omitempty"`
	NormalZ         *float64               `json:"normal_z,omitempty"`
	IconKey         *string                `json:"icon_key,omitempty"`
	ColorHex        *string                `json:"color_hex,omitempty"`
	Tags            []string               `json:"tags,omitempty"`
	CustomMetadata  map[string]interface{} `json:"custom_metadata,omitempty"`
	Attachments     []interface{}          `json:"attachments,omitempty"`
	CameraViewpoint map[string]interface{} `json:"camera_viewpoint,omitempty"`
}

type UpdatePOIInput struct {
	Title           *string                `json:"title,omitempty"`
	Description     *string                `json:"description,omitempty"`
	Category        *POICategory           `json:"category,omitempty"`
	PosX            *float64               `json:"pos_x,omitempty"`
	PosY            *float64               `json:"pos_y,omitempty"`
	PosZ            *float64               `json:"pos_z,omitempty"`
	IconKey         *string                `json:"icon_key,omitempty"`
	ColorHex        *string                `json:"color_hex,omitempty"`
	Tags            []string               `json:"tags,omitempty"`
	CustomMetadata  map[string]interface{} `json:"custom_metadata,omitempty"`
	Attachments     []interface{}          `json:"attachments,omitempty"`
	CameraViewpoint map[string]interface{} `json:"camera_viewpoint,omitempty"`
}

type SpatialSearchQuery struct {
	ProjectID      uuid.UUID    `json:"project_id"`
	Query          string       `json:"query"`
	Category       *POICategory `json:"category,omitempty"`
	LevelID        *uuid.UUID   `json:"level_id,omitempty"`
	CenterPosX     *float64     `json:"center_pos_x,omitempty"`
	CenterPosY     *float64     `json:"center_pos_y,omitempty"`
	CenterPosZ     *float64     `json:"center_pos_z,omitempty"`
	RadiusMeters   *float64     `json:"radius_meters,omitempty"`
	IncludeObjects bool         `json:"include_objects"`
}

type SearchResultItem struct {
	ID          uuid.UUID              `json:"id"`
	ResultType  string                 `json:"result_type"` // 'poi', 'section', 'level', 'structure'
	Title       string                 `json:"title"`
	Description string                 `json:"description"`
	Category    string                 `json:"category"`
	LevelName   string                 `json:"level_name,omitempty"`
	SectionName string                 `json:"section_name,omitempty"`
	Position    map[string]float64     `json:"position"`
	DistanceM        *float64               `json:"distance_meters,omitempty"`
	Score            float64                `json:"score"`
	NearestNavNodeID *uuid.UUID             `json:"nearest_nav_node_id,omitempty"`
	Meta             map[string]interface{} `json:"meta,omitempty"`
}
