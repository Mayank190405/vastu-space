package service

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"vastu/backend/internal/domain"
	"vastu/backend/internal/pkg/security"
	"vastu/backend/internal/repository"

	"github.com/google/uuid"
)

type UploadService struct {
	uploadRepo  repository.UploadRepository
	captureRepo repository.CaptureRepository
	uploadDir   string
	validator   *security.UploadSecurityValidator
}

func NewUploadService(uploadRepo repository.UploadRepository, captureRepo repository.CaptureRepository, uploadDir string) *UploadService {
	_ = os.MkdirAll(uploadDir, 0755)
	validator := security.NewUploadSecurityValidator(uploadDir)

	return &UploadService{
		uploadRepo:  uploadRepo,
		captureRepo: captureRepo,
		uploadDir:   uploadDir,
		validator:   validator,
	}
}

func (s *UploadService) InitSession(ctx context.Context, userID uuid.UUID, input domain.InitUploadInput) (*domain.UploadSession, error) {
	if input.TotalSizeBytes <= 0 && input.FileSizeBytes > 0 {
		input.TotalSizeBytes = input.FileSizeBytes
	}
	if input.SHA256Checksum == nil && input.ChecksumSHA256 != nil {
		input.SHA256Checksum = input.ChecksumSHA256
	}

	if input.FileName == "" || input.TotalSizeBytes <= 0 {
		return nil, errors.New("file_name and total_size_bytes must be valid")
	}

	if input.FileType == "" {
		ext := strings.ToLower(filepath.Ext(input.FileName))
		switch ext {
		case ".mp4", ".mov", ".m4v", ".avi":
			input.FileType = "video"
		case ".csv":
			input.FileType = "imu"
		case ".json":
			input.FileType = "manifest"
		case ".ply", ".splat", ".glb", ".gltf":
			input.FileType = "3d_model"
		default:
			input.FileType = "video"
		}
	}

	chunkSize := input.ChunkSizeBytes
	if chunkSize <= 0 {
		chunkSize = 5 * 1024 * 1024 // 5MB default chunk
	}

	totalChunks := input.TotalChunks
	if totalChunks <= 0 {
		totalChunks = int((input.TotalSizeBytes + chunkSize - 1) / chunkSize)
	}

	sessionID := uuid.New()
	safeFileName := fmt.Sprintf("%s_%s", sessionID.String()[:8], filepath.Base(input.FileName))
	// Initial target is in the Quarantine staging folder
	quarantinePath := filepath.Join(s.validator.QuarantineDir, safeFileName)
	urlTemplate := fmt.Sprintf("/api/v1/uploads/%s/chunk/{chunkIndex}", sessionID.String())

	session := &domain.UploadSession{
		ID:                sessionID,
		CaptureID:         input.CaptureID,
		UserID:            &userID,
		FileName:          input.FileName,
		FileType:          input.FileType,
		TotalSizeBytes:    input.TotalSizeBytes,
		FileSizeBytes:     input.TotalSizeBytes,
		ChunkSizeBytes:    chunkSize,
		TotalChunks:       totalChunks,
		UploadedChunks:    0,
		SHA256Checksum:    input.SHA256Checksum,
		TargetStoragePath: quarantinePath,
		Status:            domain.UploadStatusInProgress,
		UploadURLTemplate: &urlTemplate,
		ExpiresAt:         time.Now().UTC().Add(24 * time.Hour),
	}

	if err := s.uploadRepo.CreateSession(ctx, session); err != nil {
		return nil, err
	}

	return session, nil
}

func (s *UploadService) SaveChunk(ctx context.Context, sessionID uuid.UUID, chunkIndex int, expectedChecksum string, reader io.Reader) (*domain.UploadChunk, error) {
	session, err := s.uploadRepo.GetSessionByID(ctx, sessionID)
	if err != nil {
		return nil, err
	}

	if session.Status != domain.UploadStatusInProgress {
		return nil, errors.New("upload session is not active")
	}

	if chunkIndex < 0 || chunkIndex >= session.TotalChunks {
		return nil, fmt.Errorf("chunk index %d out of bounds (total %d)", chunkIndex, session.TotalChunks)
	}

	// Idempotent duplicate check: if chunk already uploaded, return without re-writing
	existingChunks, _ := s.uploadRepo.ListChunksBySession(ctx, sessionID)
	for _, c := range existingChunks {
		if c.ChunkIndex == chunkIndex && c.IsUploaded {
			return c, nil
		}
	}

	// Create session chunks staging directory
	chunkDir := filepath.Join(s.uploadDir, "chunks", sessionID.String())
	_ = os.MkdirAll(chunkDir, 0755)

	chunkPath := filepath.Join(chunkDir, fmt.Sprintf("chunk_%06d.part", chunkIndex))
	file, err := os.Create(chunkPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	hasher := sha256.New()
	multiWriter := io.MultiWriter(file, hasher)

	written, err := io.Copy(multiWriter, reader)
	if err != nil {
		return nil, err
	}

	hashStr := hex.EncodeToString(hasher.Sum(nil))

	// Verify chunk checksum if provided by client (X-Chunk-SHA256)
	if expectedChecksum != "" && !strings.EqualFold(hashStr, strings.TrimSpace(expectedChecksum)) {
		_ = os.Remove(chunkPath)
		return nil, fmt.Errorf("chunk checksum mismatch: expected %s, got %s", expectedChecksum, hashStr)
	}

	chunk := &domain.UploadChunk{
		ID:            uuid.New(),
		SessionID:     sessionID,
		ChunkIndex:    chunkIndex,
		SizeBytes:     written,
		SHA256Hash:    &hashStr,
		ChunkFilePath: chunkPath,
		IsUploaded:    true,
		UploadedAt:    time.Now().UTC(),
	}

	if err := s.uploadRepo.SaveChunk(ctx, chunk); err != nil {
		return nil, err
	}

	// Update uploaded chunk count
	chunks, _ := s.uploadRepo.ListChunksBySession(ctx, sessionID)
	_ = s.uploadRepo.UpdateSessionStatus(ctx, sessionID, domain.UploadStatusInProgress, len(chunks))

	return chunk, nil
}

func (s *UploadService) GetProgress(ctx context.Context, sessionID uuid.UUID) (*domain.UploadProgressResponse, error) {
	session, err := s.uploadRepo.GetSessionByID(ctx, sessionID)
	if err != nil {
		return nil, err
	}

	chunks, err := s.uploadRepo.ListChunksBySession(ctx, sessionID)
	if err != nil {
		return nil, err
	}

	uploadedMap := make(map[int]bool)
	for _, c := range chunks {
		uploadedMap[c.ChunkIndex] = true
	}

	var missing []int
	for i := 0; i < session.TotalChunks; i++ {
		if !uploadedMap[i] {
			missing = append(missing, i)
		}
	}

	var completedURL *string
	if session.Status == domain.UploadStatusCompleted {
		url := "/uploads/clean/" + filepath.Base(session.TargetStoragePath)
		completedURL = &url
	}

	return &domain.UploadProgressResponse{
		SessionID:      session.ID,
		TotalChunks:    session.TotalChunks,
		UploadedChunks: len(chunks),
		MissingChunks:  missing,
		Status:         session.Status,
		CompletedURL:   completedURL,
	}, nil
}

func (s *UploadService) CompleteUpload(ctx context.Context, sessionID uuid.UUID, finalChecksum string) (string, error) {
	session, err := s.uploadRepo.GetSessionByID(ctx, sessionID)
	if err != nil {
		return "", err
	}

	chunks, err := s.uploadRepo.ListChunksBySession(ctx, sessionID)
	if err != nil {
		return "", err
	}

	if len(chunks) < session.TotalChunks {
		return "", fmt.Errorf("cannot finalize: %d of %d chunks uploaded", len(chunks), session.TotalChunks)
	}

	_ = s.uploadRepo.UpdateSessionStatus(ctx, sessionID, domain.UploadStatusAssembling, len(chunks))

	// Step 1: Assemble chunks into Quarantine file
	quarantineFilePath := session.TargetStoragePath
	destFile, err := os.Create(quarantineFilePath)
	if err != nil {
		return "", fmt.Errorf("failed creating quarantined destination: %w", err)
	}

	chunkDir := filepath.Join(s.uploadDir, "chunks", sessionID.String())

	for i := 0; i < session.TotalChunks; i++ {
		chunkPath := filepath.Join(chunkDir, fmt.Sprintf("chunk_%06d.part", i))
		cFile, err := os.Open(chunkPath)
		if err != nil {
			destFile.Close()
			return "", fmt.Errorf("failed opening chunk %d: %w", i, err)
		}
		_, copyErr := io.Copy(destFile, cFile)
		cFile.Close()
		if copyErr != nil {
			destFile.Close()
			return "", fmt.Errorf("failed writing chunk %d: %w", i, copyErr)
		}
	}
	destFile.Close()

	// Clean up temporary chunk pieces
	go func() {
		_ = os.RemoveAll(chunkDir)
	}()

	// Step 2: Run Multi-Stage Security Validation (Quarantine -> Clean)
	expectedHash := finalChecksum
	if expectedHash == "" && session.SHA256Checksum != nil {
		expectedHash = *session.SHA256Checksum
	}

	valResult, promotedCleanPath, valErr := s.validator.ValidateAndPromote(
		quarantineFilePath,
		session.FileType,
		expectedHash,
	)

	if valErr != nil || !valResult.IsValid {
		_ = os.Remove(quarantineFilePath) // Purge rejected file
		_ = s.uploadRepo.UpdateSessionStatus(ctx, sessionID, domain.UploadStatusAborted, len(chunks))
		return "", fmt.Errorf("upload security validation rejected: %s", valResult.ErrorMessage)
	}

	// Step 3: Successfully Approved & Promoted
	session.TargetStoragePath = promotedCleanPath
	_ = s.uploadRepo.UpdateSessionStatus(ctx, sessionID, domain.UploadStatusCompleted, len(chunks))

	fileURL := "/uploads/clean/" + filepath.Base(promotedCleanPath)

	// Step 4: Transition Capture to ready for processing
	if session.CaptureID != nil && s.captureRepo != nil {
		switch session.FileType {
		case "video":
			_ = s.captureRepo.UpdateStatus(ctx, *session.CaptureID, domain.CaptureStatusUploaded, nil, nil, &fileURL, nil, nil)
		case "imu":
			_ = s.captureRepo.UpdateStatus(ctx, *session.CaptureID, domain.CaptureStatusUploaded, nil, nil, nil, &fileURL, nil)
		case "lidar":
			_ = s.captureRepo.UpdateStatus(ctx, *session.CaptureID, domain.CaptureStatusUploaded, nil, nil, nil, nil, &fileURL)
		case "manifest":
			_ = s.captureRepo.UpdateStatus(ctx, *session.CaptureID, domain.CaptureStatusUploaded, nil, &fileURL, nil, nil, nil)
		default:
			_ = s.captureRepo.UpdateStatus(ctx, *session.CaptureID, domain.CaptureStatusUploaded, nil, nil, &fileURL, nil, nil)
		}
	}

	return fileURL, nil
}
