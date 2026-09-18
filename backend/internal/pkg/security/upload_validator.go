package security

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type ValidationResult struct {
	IsValid      bool     `json:"is_valid"`
	DetectedMIME string   `json:"detected_mime"`
	FileSizeBytes int64   `json:"file_size_bytes"`
	SHA256Hash   string   `json:"sha256_hash"`
	Warnings     []string `json:"warnings,omitempty"`
	ErrorMessage string   `json:"error_message,omitempty"`
}

type UploadSecurityValidator struct {
	QuarantineDir string
	CleanDir      string
	MaxVideoBytes int64 // default 5GB
	MaxIMUBytes   int64 // default 200MB
	MaxJSONBytes  int64 // default 10MB
}

func NewUploadSecurityValidator(baseDir string) *UploadSecurityValidator {
	quarantineDir := filepath.Join(baseDir, "quarantine")
	cleanDir := filepath.Join(baseDir, "clean")
	_ = os.MkdirAll(quarantineDir, 0755)
	_ = os.MkdirAll(cleanDir, 0755)

	return &UploadSecurityValidator{
		QuarantineDir: quarantineDir,
		CleanDir:      cleanDir,
		MaxVideoBytes: 5 * 1024 * 1024 * 1024, // 5GB
		MaxIMUBytes:   200 * 1024 * 1024,      // 200MB
		MaxJSONBytes:  10 * 1024 * 1024,       // 10MB
	}
}

// Executable / malicious file magic byte signatures that must never be permitted
var blacklistedSignatures = [][]byte{
	{0x7F, 0x45, 0x4C, 0x46},                         // ELF executable
	{0x4D, 0x5A},                                     // DOS / Windows PE executable
	{0xFE, 0xED, 0xFA, 0xCE},                         // Mach-O 32-bit (macOS)
	{0xFE, 0xED, 0xFA, 0xCF},                         // Mach-O 64-bit (macOS)
	{0xCE, 0xFA, 0xED, 0xFE},                         // Mach-O 32-bit rev
	{0xCF, 0xFA, 0xED, 0xFE},                         // Mach-O 64-bit rev
	{0xCA, 0xFE, 0xBA, 0xBE},                         // Mach-O Universal Binary / Java Class
	{0x50, 0x4B, 0x03, 0x04},                         // ZIP / JAR (unless explicitly handled)
	[]byte("<?php"),                                  // PHP script
	[]byte("<script"),                                // Inline HTML script
	[]byte("#!/bin/sh"),                              // Shell script
	[]byte("#!/bin/bash"),                            // Bash script
	[]byte("#!/usr/bin/env"),                         // Env script
}

func (v *UploadSecurityValidator) ValidateAndPromote(
	quarantineFilePath string,
	fileType string,
	expectedChecksum string,
) (*ValidationResult, string, error) {
	result := &ValidationResult{IsValid: false}

	file, err := os.Open(quarantineFilePath)
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("failed to open quarantined file: %v", err)
		return result, "", err
	}
	defer file.Close()

	stat, err := file.Stat()
	if err != nil {
		result.ErrorMessage = fmt.Sprintf("failed to stat file: %v", err)
		return result, "", err
	}

	result.FileSizeBytes = stat.Size()

	// 1. Size Validation
	if stat.Size() == 0 {
		result.ErrorMessage = "file size is 0 bytes (empty file)"
		return result, "", errors.New(result.ErrorMessage)
	}

	switch strings.ToLower(fileType) {
	case "video", "rgb_video", "video_rgb_imu":
		if stat.Size() < 100*1024 { // Min 100KB
			result.ErrorMessage = fmt.Sprintf("video file too small (%d bytes), minimum 100KB required", stat.Size())
			return result, "", errors.New(result.ErrorMessage)
		}
		if stat.Size() > v.MaxVideoBytes {
			result.ErrorMessage = fmt.Sprintf("video file exceeds maximum size limit of %d bytes", v.MaxVideoBytes)
			return result, "", errors.New(result.ErrorMessage)
		}
	case "imu", "imu_stream", "csv":
		if stat.Size() > v.MaxIMUBytes {
			result.ErrorMessage = fmt.Sprintf("IMU file exceeds maximum size limit of %d bytes", v.MaxIMUBytes)
			return result, "", errors.New(result.ErrorMessage)
		}
	case "manifest", "metadata", "json":
		if stat.Size() > v.MaxJSONBytes {
			result.ErrorMessage = fmt.Sprintf("metadata JSON exceeds maximum size limit of %d bytes", v.MaxJSONBytes)
			return result, "", errors.New(result.ErrorMessage)
		}
	}

	// 2. Read first 512 bytes for Magic Bytes & MIME inspection
	headerBuf := make([]byte, 512)
	n, err := file.Read(headerBuf)
	if err != nil && err != io.EOF {
		result.ErrorMessage = "failed reading file header buffer"
		return result, "", err
	}
	headerBuf = headerBuf[:n]

	// 3. Malware / Executable signature check
	for _, sig := range blacklistedSignatures {
		if bytes.HasPrefix(headerBuf, sig) || bytes.Contains(headerBuf, sig) {
			result.ErrorMessage = "file rejected: contains blacklisted binary executable or script payload"
			return result, "", errors.New(result.ErrorMessage)
		}
	}

	// 4. MIME & Magic-byte validation based on expected file type
	detectedMIME := http.DetectContentType(headerBuf)
	result.DetectedMIME = detectedMIME

	switch strings.ToLower(fileType) {
	case "video", "rgb_video", "video_rgb_imu":
		// Check for ISO Base Media File Format (ftyp box: bytes 4..7 must be 'ftyp')
		hasFtyp := len(headerBuf) >= 8 && string(headerBuf[4:8]) == "ftyp"
		hasMoov := bytes.Contains(headerBuf, []byte("moov")) || bytes.Contains(headerBuf, []byte("mdat"))
		if !hasFtyp && !hasMoov && !strings.Contains(detectedMIME, "video") && !strings.Contains(detectedMIME, "octet-stream") {
			result.ErrorMessage = fmt.Sprintf("invalid video magic bytes (detected MIME: %s)", detectedMIME)
			return result, "", errors.New(result.ErrorMessage)
		}
	case "imu", "imu_stream", "csv":
		if !strings.HasPrefix(detectedMIME, "text/") && !strings.Contains(detectedMIME, "octet-stream") {
			result.ErrorMessage = fmt.Sprintf("invalid IMU CSV MIME type: %s", detectedMIME)
			return result, "", errors.New(result.ErrorMessage)
		}
		// Verify expected CSV header text
		headerStr := string(headerBuf)
		if !strings.Contains(headerStr, "timestamp_ns") && !strings.Contains(headerStr, "accel") {
			result.ErrorMessage = "invalid IMU CSV header format: expected timestamp_ns column"
			return result, "", errors.New(result.ErrorMessage)
		}
	case "manifest", "metadata", "json":
		trimmed := bytes.TrimSpace(headerBuf)
		if len(trimmed) == 0 || (trimmed[0] != '{' && trimmed[0] != '[') {
			result.ErrorMessage = "invalid JSON format: expected leading '{' or '['"
			return result, "", errors.New(result.ErrorMessage)
		}
	}

	// 5. Compute and verify SHA256 checksum over entire file
	_, err = file.Seek(0, io.SeekStart)
	if err != nil {
		result.ErrorMessage = "failed seeking file start"
		return result, "", err
	}

	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		result.ErrorMessage = "failed computing SHA256 checksum"
		return result, "", err
	}
	calculatedHash := hex.EncodeToString(hasher.Sum(nil))
	result.SHA256Hash = calculatedHash

	if expectedChecksum != "" && !strings.EqualFold(calculatedHash, strings.TrimSpace(expectedChecksum)) {
		result.Warnings = append(result.Warnings, fmt.Sprintf("client whole-file checksum notice: client provided %s, assembled hash is %s", expectedChecksum, calculatedHash))
	}

	// 6. All validation checks passed: Promote from Quarantine to Clean Storage
	file.Close()

	cleanFileName := filepath.Base(quarantineFilePath)
	promotedPath := filepath.Join(v.CleanDir, cleanFileName)

	if err := os.Rename(quarantineFilePath, promotedPath); err != nil {
		// Fallback to copy and remove if across filesystems
		if copyErr := copyFile(quarantineFilePath, promotedPath); copyErr != nil {
			result.ErrorMessage = fmt.Sprintf("failed promoting validated file to clean storage: %v", copyErr)
			return result, "", copyErr
		}
		_ = os.Remove(quarantineFilePath)
	}

	result.IsValid = true
	return result, promotedPath, nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}
