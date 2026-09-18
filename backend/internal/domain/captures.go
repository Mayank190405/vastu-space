package domain

import (
	"time"

	"github.com/google/uuid"
)

type CaptureStatus string

const (
	CaptureStatusRecording  CaptureStatus = "recording"
	CaptureStatusUploaded   CaptureStatus = "uploaded"
	CaptureStatusValidating CaptureStatus = "validating"
	CaptureStatusProcessing CaptureStatus = "processing"
	CaptureStatusCompleted  CaptureStatus = "completed"
	CaptureStatusFailed     CaptureStatus = "failed"
)

type CaptureMode string

const (
	CaptureModeRGBIMU         CaptureMode = "rgb_imu"
	CaptureModeRGBLiDAR       CaptureMode = "rgb_lidar"
	CaptureModeRescanTargeted CaptureMode = "rescan_targeted"
)

type CameraIntrinsics struct {
	FX         float64   `json:"fx"`
	FY         float64   `json:"fy"`
	CX         float64   `json:"cx"`
	CY         float64   `json:"cy"`
	Distortion []float64 `json:"distortion"`
	Width      int       `json:"width"`
	Height     int       `json:"height"`
}

type Capture struct {
	ID                     uuid.UUID         `json:"id"`
	ProjectID              uuid.UUID         `json:"project_id"`
	StructureID            *uuid.UUID        `json:"structure_id,omitempty"`
	LevelID                *uuid.UUID        `json:"level_id,omitempty"`
	SectionID              *uuid.UUID        `json:"section_id,omitempty"`
	OperatorID             *uuid.UUID        `json:"operator_id,omitempty"`
	DeviceModel            string            `json:"device_model"`
	DeviceOS               string            `json:"device_os"`
	DeviceAppVersion       string            `json:"device_app_version"`
	CameraIntrinsics       *CameraIntrinsics `json:"camera_intrinsics,omitempty"`
	IMURateHz              int               `json:"imu_rate_hz"`
	HasLiDAR               bool              `json:"has_lidar"`
	CaptureMode            CaptureMode       `json:"capture_mode"`
	DurationSeconds        float64           `json:"duration_seconds"`
	FramesCount            int               `json:"frames_count"`
	FileSizeBytes          int64             `json:"file_size_bytes"`
	TrajectoryLengthMeters float64           `json:"trajectory_length_meters"`
	QualityScore           float64           `json:"quality_score"`
	BlurScore              float64           `json:"blur_score"`
	LightingScore          float64           `json:"lighting_score"`
	Status                 CaptureStatus     `json:"status"`
	ManifestURL            *string           `json:"manifest_url,omitempty"`
	VideoURL               *string           `json:"video_url,omitempty"`
	IMUURL                 *string           `json:"imu_url,omitempty"`
	LiDARURL               *string           `json:"lidar_url,omitempty"`
	Notes                  *string           `json:"notes,omitempty"`
	CreatedAt              time.Time         `json:"created_at"`
	UpdatedAt              time.Time         `json:"updated_at"`
}

type CreateCaptureInput struct {
	ProjectID              uuid.UUID         `json:"project_id"`
	StructureID            *uuid.UUID        `json:"structure_id,omitempty"`
	LevelID                *uuid.UUID        `json:"level_id,omitempty"`
	SectionID              *uuid.UUID        `json:"section_id,omitempty"`
	DeviceModel            string            `json:"device_model"`
	DeviceOS               string            `json:"device_os"`
	DeviceAppVersion       string            `json:"device_app_version"`
	CameraIntrinsics       *CameraIntrinsics `json:"camera_intrinsics,omitempty"`
	IMURateHz              int               `json:"imu_rate_hz"`
	HasLiDAR               bool              `json:"has_lidar"`
	CaptureMode            CaptureMode       `json:"capture_mode"`
	DurationSeconds        float64           `json:"duration_seconds"`
	FramesCount            int               `json:"frames_count"`
	FileSizeBytes          int64             `json:"file_size_bytes"`
	TrajectoryLengthMeters float64           `json:"trajectory_length_meters"`
	QualityScore           float64           `json:"quality_score"`
	BlurScore              float64           `json:"blur_score"`
	LightingScore          float64           `json:"lighting_score"`
	Notes                  *string           `json:"notes,omitempty"`
}

type UpdateCaptureStatusInput struct {
	Status       CaptureStatus `json:"status"`
	QualityScore *float64      `json:"quality_score,omitempty"`
	ManifestURL  *string       `json:"manifest_url,omitempty"`
	VideoURL     *string       `json:"video_url,omitempty"`
	IMUURL       *string       `json:"imu_url,omitempty"`
	LiDARURL     *string       `json:"lidar_url,omitempty"`
}
