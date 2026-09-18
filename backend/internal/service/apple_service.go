package service

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"strings"
)

type AppleService struct {
	clientID string
}

type AppleUserPayload struct {
	Email         string
	EmailVerified bool
	Name          string
	Subject       string // Apple unique user ID (sub)
}

func NewAppleService(clientID string) *AppleService {
	return &AppleService{clientID: clientID}
}

func (s *AppleService) ValidateIDToken(ctx context.Context, idTokenString, fullName string) (*AppleUserPayload, error) {
	if strings.TrimSpace(idTokenString) == "" {
		return nil, errors.New("empty apple id_token")
	}

	// Apple ID Token is a standard 3-part JWT: header.payload.signature
	parts := strings.Split(idTokenString, ".")
	if len(parts) < 2 {
		return nil, errors.New("invalid apple id_token format")
	}

	// Ensure base64 padding if needed
	payloadSeg := parts[1]
	if l := len(payloadSeg) % 4; l > 0 {
		payloadSeg += strings.Repeat("=", 4-l)
	}

	payloadBytes, err := base64.URLEncoding.DecodeString(payloadSeg)
	if err != nil {
		payloadBytes, err = base64.RawURLEncoding.DecodeString(parts[1])
		if err != nil {
			return nil, errors.New("failed to decode apple token payload")
		}
	}

	var claims struct {
		Sub           string      `json:"sub"`
		Email         string      `json:"email"`
		EmailVerified interface{} `json:"email_verified"`
	}

	if err := json.Unmarshal(payloadBytes, &claims); err != nil {
		return nil, errors.New("malformed apple token claims")
	}

	if claims.Sub == "" {
		return nil, errors.New("apple token missing sub claim")
	}

	var isVerified bool
	switch v := claims.EmailVerified.(type) {
	case bool:
		isVerified = v
	case string:
		isVerified = v == "true"
	}

	userName := strings.TrimSpace(fullName)
	if userName == "" {
		if claims.Email != "" {
			prefix := strings.Split(claims.Email, "@")[0]
			userName = strings.ToUpper(prefix[:1]) + prefix[1:]
		} else {
			userName = "Apple User"
		}
	}

	return &AppleUserPayload{
		Email:         claims.Email,
		EmailVerified: isVerified,
		Name:          userName,
		Subject:       claims.Sub,
	}, nil
}
