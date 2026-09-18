package domain

import (
	"time"

	"github.com/google/uuid"
)

type NavNodeType string

const (
	NavNodeTypeWalkway      NavNodeType = "walkway"
	NavNodeTypeDoor         NavNodeType = "door"
	NavNodeTypeIntersection NavNodeType = "intersection"
	NavNodeTypeStairEntry   NavNodeType = "stair_entry"
	NavNodeTypeElevatorDoor NavNodeType = "elevator_door"
	NavNodeTypeRampEntry    NavNodeType = "ramp_entry"
	NavNodeTypePOIAnchor    NavNodeType = "poi_anchor"
)

type NavEdgeType string

const (
	NavEdgeTypeCorridor NavEdgeType = "corridor"
	NavEdgeTypeDoor     NavEdgeType = "door"
	NavEdgeTypeStairs   NavEdgeType = "stairs"
	NavEdgeTypeElevator NavEdgeType = "elevator"
	NavEdgeTypeRamp     NavEdgeType = "ramp"
)

type NavNode struct {
	ID                     uuid.UUID   `json:"id"`
	ProjectID              uuid.UUID   `json:"project_id"`
	LevelID                *uuid.UUID  `json:"level_id,omitempty"`
	SectionID              *uuid.UUID  `json:"section_id,omitempty"`
	NodeType               NavNodeType `json:"node_type"`
	PosX                   float64     `json:"pos_x"`
	PosY                   float64     `json:"pos_y"`
	PosZ                   float64     `json:"pos_z"`
	IsWheelchairAccessible bool        `json:"is_wheelchair_accessible"`
	CreatedAt              time.Time   `json:"created_at"`
}

type NavEdge struct {
	ID                     uuid.UUID   `json:"id"`
	ProjectID              uuid.UUID   `json:"project_id"`
	FromNodeID             uuid.UUID   `json:"from_node_id"`
	ToNodeID               uuid.UUID   `json:"to_node_id"`
	EdgeType               NavEdgeType `json:"edge_type"`
	DistanceMeters         float64     `json:"distance_meters"`
	IsBidirectional        bool        `json:"is_bidirectional"`
	IsWheelchairAccessible bool        `json:"is_wheelchair_accessible"`
	WeightModifier         float64     `json:"weight_modifier"`
	CreatedAt              time.Time   `json:"created_at"`
}

type NavRouteRequest struct {
	ProjectID              uuid.UUID  `json:"project_id"`
	StartPosX              float64    `json:"start_pos_x"`
	StartPosY              float64    `json:"start_pos_y"`
	StartPosZ              float64    `json:"start_pos_z"`
	TargetPosX             float64    `json:"target_pos_x"`
	TargetPosY             float64    `json:"target_pos_y"`
	TargetPosZ             float64    `json:"target_pos_z"`
	StartPOIID             *uuid.UUID `json:"start_poi_id,omitempty"`
	TargetPOIID            *uuid.UUID `json:"target_poi_id,omitempty"`
	RequireWheelchair      bool       `json:"require_wheelchair"`
	AvoidStairs            bool       `json:"avoid_stairs"`
}

type RouteStep struct {
	StepIndex        int                `json:"step_index"`
	Instruction      string             `json:"instruction"`
	TurnType         string             `json:"turn_type"` // 'straight', 'turn_left', 'turn_right', 'take_stairs_up', 'take_stairs_down', 'take_elevator', 'arrive'
	DistanceMeters   float64            `json:"distance_meters"`
	FromPosition     map[string]float64 `json:"from_position"`
	ToPosition       map[string]float64 `json:"to_position"`
	LevelTransition  *string            `json:"level_transition,omitempty"`
}

type NavRouteResponse struct {
	ProjectID              uuid.UUID            `json:"project_id"`
	TotalDistanceMeters    float64              `json:"total_distance_meters"`
	EstimatedWalkSeconds   int                  `json:"estimated_walk_seconds"`
	IsWheelchairAccessible bool                 `json:"is_wheelchair_accessible"`
	Waypoints              []map[string]float64 `json:"waypoints"`
	Steps                  []RouteStep          `json:"steps"`
}
