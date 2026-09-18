package tests

import (
	"os"
	"path/filepath"
	"testing"
	"vastu/backend/internal/pkg/security"

	"github.com/stretchr/testify/assert"
)

// TestStorageSecurity targets Phase 4.3 - FILE SECURITY
func TestStorageSecurity(t *testing.T) {
	tempDir := t.TempDir()
	validator := security.NewUploadSecurityValidator(tempDir)
	
	t.Run("Malware ELF Payload Rejected", func(t *testing.T) {
		quarantineFile := filepath.Join(tempDir, "quarantine", "malware.bin")
		// Simulate Linux ELF binary magic bytes (with >=100KB size so it passes size check and triggers executable blacklist)
		payload := make([]byte, 105*1024)
		copy(payload, []byte{0x7F, 0x45, 0x4C, 0x46, 0x01, 0x01, 0x01})
		err := os.WriteFile(quarantineFile, payload, 0644)
		assert.NoError(t, err)

		res, _, err := validator.ValidateAndPromote(quarantineFile, "video", "")
		assert.Error(t, err)
		assert.False(t, res.IsValid)
		assert.Contains(t, res.ErrorMessage, "blacklisted binary executable")
	})
	
	t.Run("PHP Script Payload Rejected", func(t *testing.T) {
		quarantineFile := filepath.Join(tempDir, "quarantine", "script.php")
		payload := []byte("<?php system($_GET['cmd']); ?>")
		os.WriteFile(quarantineFile, payload, 0644)

		res, _, err := validator.ValidateAndPromote(quarantineFile, "metadata", "")
		assert.Error(t, err)
		assert.False(t, res.IsValid)
		assert.Contains(t, res.ErrorMessage, "blacklisted binary executable or script")
	})
	
	t.Run("Zero Byte File Rejected", func(t *testing.T) {
		quarantineFile := filepath.Join(tempDir, "quarantine", "empty.mp4")
		os.WriteFile(quarantineFile, []byte{}, 0644)

		res, _, err := validator.ValidateAndPromote(quarantineFile, "video", "")
		assert.Error(t, err)
		assert.False(t, res.IsValid)
		assert.Contains(t, res.ErrorMessage, "size is 0 bytes")
	})
	
	t.Run("Valid MP4 Moves to Clean Storage", func(t *testing.T) {
		quarantineFile := filepath.Join(tempDir, "quarantine", "valid.mp4")
		// Simulate valid MP4 with ftyp box
		payload := make([]byte, 150000) // 150KB to pass size check
		copy(payload[4:8], []byte("ftyp"))
		copy(payload[8:12], []byte("moov"))
		os.WriteFile(quarantineFile, payload, 0644)

		res, promotedPath, err := validator.ValidateAndPromote(quarantineFile, "video", "")
		assert.NoError(t, err)
		assert.True(t, res.IsValid)
		
		// Assert file was moved
		_, err = os.Stat(promotedPath)
		assert.NoError(t, err, "File should exist in clean directory")
		
		_, err = os.Stat(quarantineFile)
		assert.Error(t, err, "File should be removed from quarantine directory")
	})
}
