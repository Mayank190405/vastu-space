package utils

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"regexp"
	"strings"
)

const alphaNumCharset = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

var (
	nonAlphaNum = regexp.MustCompile(`[^A-Za-z0-9]+`)
)

func GenerateOTP() (string, error) {
	n, err := rand.Int(rand.Reader, big.NewInt(900000))
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%06d", n.Int64()+100000), nil
}

func RandomAlphaNum(length int) string {
	return randomAlphaNum(length)
}

func Slugify(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	s = nonAlphaNum.ReplaceAllString(s, "-")
	return strings.Trim(s, "-")
}

func randomAlphaNum(length int) string {

	b := make([]byte, length)
	charsetLen := big.NewInt(int64(len(alphaNumCharset)))
	for i := 0; i < length; i++ {
		n, err := rand.Int(rand.Reader, charsetLen)
		if err != nil {
			b[i] = alphaNumCharset[0]
			continue
		}
		b[i] = alphaNumCharset[n.Int64()]
	}
	return string(b)
}

// GenerateOrgCode creates a unique VASTU formatted organization identifier:
// V(4 alphanumeric)A(4 alphanumeric)S(4 alphanumeric)T(4 alphanumeric)U (e.g. V8A2KA9X1PS4M90TB7W2U)
func GenerateOrgCode(orgName string) string {
	part1 := randomAlphaNum(4)
	part2 := randomAlphaNum(4)
	part3 := randomAlphaNum(4)
	part4 := randomAlphaNum(4)

	return fmt.Sprintf("V%sA%sS%sT%sU", part1, part2, part3, part4)
}

// FormatOrgCode formats raw alphanumeric string into V-XXXX-A-XXXX-S-XXXX-T-XXXX-U
func FormatOrgCode(raw string) string {
	clean := strings.ToUpper(nonAlphaNum.ReplaceAllString(raw, ""))
	if len(clean) == 21 && strings.HasPrefix(clean, "V") && clean[5] == 'A' && clean[10] == 'S' && clean[15] == 'T' && strings.HasSuffix(clean, "U") {
		return fmt.Sprintf("V-%s-A-%s-S-%s-T-%s-U", clean[1:5], clean[6:10], clean[11:15], clean[16:20])
	}
	return clean
}
