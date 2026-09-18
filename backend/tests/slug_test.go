package tests

import (
	"strings"
	"testing"

	"vastu/backend/internal/pkg/utils"
)

func TestGenerateOTP(t *testing.T) {
	otp, err := utils.GenerateOTP()
	if err != nil {
		t.Fatalf("failed to generate OTP: %v", err)
	}

	if len(otp) != 6 {
		t.Fatalf("expected 6-digit OTP, got length: %d (%s)", len(otp), otp)
	}

	for _, c := range otp {
		if c < '0' || c > '9' {
			t.Fatalf("expected only digits in OTP, found: %c", c)
		}
	}
}

func TestSlugify(t *testing.T) {
	slug := utils.Slugify("Acme Robotics & Spatial Corp")
	if slug != "acme-robotics-spatial-corp" {
		t.Fatalf("unexpected slug format: %s", slug)
	}
}

func TestGenerateOrgCode(t *testing.T) {
	code := utils.GenerateOrgCode("Acme Robotics & Spatial Corp")
	if len(code) != 21 || !strings.HasPrefix(code, "V") || !strings.HasSuffix(code, "U") {
		t.Fatalf("unexpected org code format: %s", code)
	}

	formatted := utils.FormatOrgCode(code)
	if !strings.HasPrefix(formatted, "V-") || !strings.HasSuffix(formatted, "-U") {
		t.Fatalf("unexpected formatted org code: %s", formatted)
	}
}
