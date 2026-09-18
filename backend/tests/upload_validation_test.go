package tests

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"testing"

	"vastu/backend/internal/pkg/security"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUploadSecurityValidator(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "vastu_upload_test_*")
	require.NoError(t, err)
	defer os.RemoveAll(tempDir)

	validator := security.NewUploadSecurityValidator(tempDir)
	// Set lower video min size for test convenience
	validator.MaxVideoBytes = 10 * 1024 * 1024 // 10MB

	t.Run("TC01: Valid Video Upload with ftyp Header", func(t *testing.T) {
		// Mock a valid MP4 header (size 8 bytes ftyp box + padding)
		data := make([]byte, 120*1024) // 120KB
		copy(data[0:8], []byte("\x00\x00\x00\x20ftypisom"))

		hasher := sha256.New()
		hasher.Write(data)
		expectedHash := hex.EncodeToString(hasher.Sum(nil))

		quarantinePath := filepath.Join(validator.QuarantineDir, "valid_video.mp4")
		err := os.WriteFile(quarantinePath, data, 0644)
		require.NoError(t, err)

		res, cleanPath, err := validator.ValidateAndPromote(quarantinePath, "video", expectedHash)
		assert.NoError(t, err)
		assert.True(t, res.IsValid)
		assert.FileExists(t, cleanPath)
		assert.NoFileExists(t, quarantinePath)
	})

	t.Run("TC02: Valid IMU CSV Stream", func(t *testing.T) {
		csvContent := "timestamp_ns,sensor_type,x,y,z,accuracy\n1725475200000000,ACCELEROMETER,0.1,9.8,0.2,3\n1725475200010000,GYROSCOPE,0.01,0.02,0.01,3\n"
		data := []byte(csvContent)

		hasher := sha256.New()
		hasher.Write(data)
		expectedHash := hex.EncodeToString(hasher.Sum(nil))

		quarantinePath := filepath.Join(validator.QuarantineDir, "valid_imu.csv")
		err := os.WriteFile(quarantinePath, data, 0644)
		require.NoError(t, err)

		res, cleanPath, err := validator.ValidateAndPromote(quarantinePath, "imu", expectedHash)
		assert.NoError(t, err)
		assert.True(t, res.IsValid)
		assert.FileExists(t, cleanPath)
	})

	t.Run("TC03: Reject Malicious Executable Disguised as MP4", func(t *testing.T) {
		// ELF executable header disguised with .mp4
		maliciousData := make([]byte, 150*1024)
		copy(maliciousData[0:4], []byte{0x7F, 0x45, 0x4C, 0x46}) // \x7fELF

		quarantinePath := filepath.Join(validator.QuarantineDir, "malware.mp4")
		err := os.WriteFile(quarantinePath, maliciousData, 0644)
		require.NoError(t, err)

		res, _, err := validator.ValidateAndPromote(quarantinePath, "video", "")
		assert.Error(t, err)
		assert.False(t, res.IsValid)
		assert.Contains(t, res.ErrorMessage, "contains blacklisted binary executable")
	})

	t.Run("TC04: Reject Malicious Shell Script Disguised as CSV", func(t *testing.T) {
		scriptData := []byte("#!/bin/bash\nrm -rf /\necho 'hacked'\n")

		quarantinePath := filepath.Join(validator.QuarantineDir, "exploit.csv")
		err := os.WriteFile(quarantinePath, scriptData, 0644)
		require.NoError(t, err)

		res, _, err := validator.ValidateAndPromote(quarantinePath, "csv", "")
		assert.Error(t, err)
		assert.False(t, res.IsValid)
		assert.Contains(t, res.ErrorMessage, "contains blacklisted binary executable or script")
	})

	t.Run("TC05: Checksum Mismatch Rejection", func(t *testing.T) {
		data := make([]byte, 120*1024)
		copy(data[0:8], []byte("\x00\x00\x00\x20ftypisom"))

		quarantinePath := filepath.Join(validator.QuarantineDir, "mismatch.mp4")
		err := os.WriteFile(quarantinePath, data, 0644)
		require.NoError(t, err)

		res, _, err := validator.ValidateAndPromote(quarantinePath, "video", "0000000000000000000000000000000000000000000000000000000000000000")
		assert.Error(t, err)
		assert.False(t, res.IsValid)
		assert.Contains(t, res.ErrorMessage, "checksum mismatch")
	})

	t.Run("TC06: Reject Oversized Upload", func(t *testing.T) {
		validator.MaxJSONBytes = 500 // Set low limit
		largeJSON := make([]byte, 2048)
		largeJSON[0] = '{'
		largeJSON[2047] = '}'

		quarantinePath := filepath.Join(validator.QuarantineDir, "large.json")
		err := os.WriteFile(quarantinePath, largeJSON, 0644)
		require.NoError(t, err)

		res, _, err := validator.ValidateAndPromote(quarantinePath, "json", "")
		assert.Error(t, err)
		assert.False(t, res.IsValid)
		assert.Contains(t, res.ErrorMessage, "exceeds maximum size limit")
	})
}
