package validator

import (
	"errors"
	"regexp"
	"strings"
	"unicode"
)

var (
	ErrPasswordTooShort     = errors.New("password must be at least 12 characters long")
	ErrPasswordTooLong      = errors.New("password must not exceed 128 characters")
	ErrPasswordNoUpper      = errors.New("password must contain at least one uppercase letter")
	ErrPasswordNoLower      = errors.New("password must contain at least one lowercase letter")
	ErrPasswordNoDigit      = errors.New("password must contain at least one number")
	ErrPasswordNoSpecial    = errors.New("password must contain at least one special character")
	ErrPasswordContainsUser = errors.New("password must not contain your email or name")
	ErrPasswordContainsOrg  = errors.New("password must not contain the organization name")
	ErrPasswordSequential   = errors.New("password must not contain obvious sequential patterns (e.g. 12345, abcde)")
	ErrPasswordExcessRepeat = errors.New("password contains excessive repeated characters")
	ErrPasswordCommon       = errors.New("password is too common or predictable")
)

var commonPasswords = map[string]bool{
	"qwerty123456!": true,
	"password1234!": true,
	"admin1234567!": true,
	"welcome12345!": true,
	"letmein12345!": true,
}

var gstinRegex = regexp.MustCompile(`^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`)
var panRegex = regexp.MustCompile(`^[A-Z]{5}[0-9]{4}[A-Z]{1}$`)

// ValidatePassword validates password strength based on production security policy
func ValidatePassword(password, email, fullName, orgName string) error {
	runes := []rune(password)
	if len(runes) < 12 {
		return ErrPasswordTooShort
	}
	if len(runes) > 128 {
		return ErrPasswordTooLong
	}

	var hasUpper, hasLower, hasDigit, hasSpecial bool
	for _, r := range runes {
		switch {
		case unicode.IsUpper(r):
			hasUpper = true
		case unicode.IsLower(r):
			hasLower = true
		case unicode.IsDigit(r):
			hasDigit = true
		case unicode.IsPunct(r) || unicode.IsSymbol(r):
			hasSpecial = true
		}
	}

	if !hasUpper {
		return ErrPasswordNoUpper
	}
	if !hasLower {
		return ErrPasswordNoLower
	}
	if !hasDigit {
		return ErrPasswordNoDigit
	}
	if !hasSpecial {
		return ErrPasswordNoSpecial
	}

	pwLower := strings.ToLower(password)

	// Check common passwords
	if commonPasswords[pwLower] {
		return ErrPasswordCommon
	}

	// Check email part
	if email != "" {
		parts := strings.Split(strings.ToLower(email), "@")
		if len(parts) > 0 && len(parts[0]) >= 3 && strings.Contains(pwLower, parts[0]) {
			return ErrPasswordContainsUser
		}
	}

	// Check name parts
	if fullName != "" {
		words := strings.Fields(strings.ToLower(fullName))
		for _, w := range words {
			if len(w) >= 3 && strings.Contains(pwLower, w) {
				return ErrPasswordContainsUser
			}
		}
	}

	// Check org name
	if orgName != "" {
		words := strings.Fields(strings.ToLower(orgName))
		for _, w := range words {
			if len(w) >= 4 && strings.Contains(pwLower, w) {
				return ErrPasswordContainsOrg
			}
		}
	}

	// Check excessive repeating characters (5 or more identical consecutive characters)
	repeatCount := 1
	var lastRune rune
	for _, r := range runes {
		if r == lastRune {
			repeatCount++
			if repeatCount >= 5 {
				return ErrPasswordExcessRepeat
			}
		} else {
			repeatCount = 1
			lastRune = r
		}
	}

	// Check sequential patterns like "12345", "abcdef", "54321", "fedcb"
	if hasSequentialPattern(pwLower, 5) {
		return ErrPasswordSequential
	}

	return nil
}

func hasSequentialPattern(s string, threshold int) bool {
	runes := []rune(s)
	if len(runes) < threshold {
		return false
	}

	for i := 0; i <= len(runes)-threshold; i++ {
		asc := true
		desc := true
		for j := 0; j < threshold-1; j++ {
			r1 := runes[i+j]
			r2 := runes[i+j+1]
			if r2 != r1+1 {
				asc = false
			}
			if r2 != r1-1 {
				desc = false
			}
		}
		if asc || desc {
			return true
		}
	}
	return false
}

// ValidateGSTIN validates standard Indian 15-character GST identification number
func ValidateGSTIN(gstin string) bool {
	clean := strings.ToUpper(strings.TrimSpace(gstin))
	return gstinRegex.MatchString(clean)
}

// ValidatePAN validates standard Indian 10-character PAN number
func ValidatePAN(pan string) bool {
	clean := strings.ToUpper(strings.TrimSpace(pan))
	return panRegex.MatchString(clean)
}
