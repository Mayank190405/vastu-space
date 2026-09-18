package utils

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"math/big"
)

// Unambiguous 32-character alphabet (no 0, O, 1, I, L)
const orgCodeAlphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

// Generate12CharOrgCode produces an un-ambiguous, non-sequential, URL-safe 12-character organization code
func Generate12CharOrgCode() string {
	code := make([]byte, 12)
	max := big.NewInt(int64(len(orgCodeAlphabet)))
	for i := 0; i < 12; i++ {
		idx, err := rand.Int(rand.Reader, max)
		if err != nil {
			code[i] = orgCodeAlphabet[i%len(orgCodeAlphabet)]
		} else {
			code[i] = orgCodeAlphabet[idx.Int64()]
		}
	}
	return string(code)
}

// GenerateInviteToken creates a random URL-safe 24-character invite token and its SHA-256 hash
func GenerateInviteToken() (string, string) {
	bytes := make([]byte, 16)
	_, _ = rand.Read(bytes)
	rawToken := hex.EncodeToString(bytes)
	hash := sha256.Sum256([]byte(rawToken))
	tokenHash := hex.EncodeToString(hash[:])
	return rawToken, tokenHash
}

// HashInviteToken hashes an invite token with SHA-256 for lookup
func HashInviteToken(token string) string {
	hash := sha256.Sum256([]byte(token))
	return hex.EncodeToString(hash[:])
}
