package domain

import (
	"time"

	"github.com/google/uuid"
)

type UploadStatus string

const (
	UploadStatusInProgress UploadStatus = "in_progress"
	UploadStatusAssembling UploadStatus = "assembling"
	UploadStatusCompleted  UploadStatus = "completed"
	UploadStatusAborted    UploadStatus = "aborted"
	UploadStatusExpired    UploadStatus = "expired"
)

type UploadSession struct {
	ID                uuid.UUID    `json:"id"`
	CaptureID         *uuid.UUID   `json:"capture_id,omitempty"`
	UserID            *uuid.UUID   `json:"user_id,omitempty"`
	FileName          string       `json:"file_name"`
	FileType          string       `json:"file_type"`
	TotalSizeBytes    int64        `json:"total_size_bytes"`
	FileSizeBytes     int64        `json:"file_size_bytes"`
	ChunkSizeBytes    int64        `json:"chunk_size_bytes"`
	TotalChunks       int          `json:"total_chunks"`
	UploadedChunks    int          `json:"uploaded_chunks"`
	SHA256Checksum    *string      `json:"sha256_checksum,omitempty"`
	TargetStoragePath string       `json:"target_storage_path"`
	Status            UploadStatus `json:"status"`
	UploadURLTemplate *string      `json:"upload_url_template,omitempty"`
	ExpiresAt         time.Time    `json:"expires_at"`
	CreatedAt         time.Time    `json:"created_at"`
	UpdatedAt         time.Time    `json:"updated_at"`
}

type UploadChunk struct {
	ID            uuid.UUID `json:"id"`
	SessionID     uuid.UUID `json:"session_id"`
	ChunkIndex    int       `json:"chunk_index"`
	SizeBytes     int64     `json:"size_bytes"`
	SHA256Hash    *string   `json:"sha256_hash,omitempty"`
	ChunkFilePath string    `json:"chunk_file_path"`
	IsUploaded    bool      `json:"is_uploaded"`
	UploadedAt    time.Time `json:"uploaded_at"`
}

type InitUploadInput struct {
	CaptureID      *uuid.UUID `json:"capture_id,omitempty"`
	FileName       string     `json:"file_name"`
	FileType       string     `json:"file_type,omitempty"`
	TotalSizeBytes int64      `json:"total_size_bytes"`
	FileSizeBytes  int64      `json:"file_size_bytes,omitempty"`
	ChunkSizeBytes int64      `json:"chunk_size_bytes"`
	TotalChunks    int        `json:"total_chunks,omitempty"`
	SHA256Checksum *string    `json:"sha256_checksum,omitempty"`
	ChecksumSHA256 *string    `json:"checksum_sha256,omitempty"`
}

type CompleteUploadInput struct {
	FinalChecksumSHA256 *string `json:"final_checksum_sha256,omitempty"`
}



type UploadProgressResponse struct {
	SessionID      uuid.UUID    `json:"session_id"`
	TotalChunks    int          `json:"total_chunks"`
	UploadedChunks int          `json:"uploaded_chunks"`
	MissingChunks  []int        `json:"missing_chunks"`
	Status         UploadStatus `json:"status"`
	CompletedURL   *string      `json:"completed_url,omitempty"`
}
