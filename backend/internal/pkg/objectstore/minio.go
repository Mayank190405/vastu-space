package objectstore

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"net/url"
	"os"
	"strings"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type Store struct {
	Client    *minio.Client
	RawBucket string
}

func FromEnv() (*Store, error) {
	endpoint := os.Getenv("S3_ENDPOINT")
	if endpoint == "" {
		endpoint = os.Getenv("S3_ENDPOINT_URL")
	}
	if endpoint == "" {
		return nil, errors.New("S3_ENDPOINT is not configured")
	}
	u, err := url.Parse(endpoint)
	if err != nil || u.Host == "" {
		return nil, errors.New("invalid S3 endpoint")
	}
	key, secret := os.Getenv("AWS_ACCESS_KEY_ID"), os.Getenv("AWS_SECRET_ACCESS_KEY")
	if key == "" || secret == "" {
		return nil, errors.New("S3 credentials are not configured")
	}
	client, err := minio.New(u.Host, &minio.Options{Creds: credentials.NewStaticV4(key, secret, ""), Secure: u.Scheme == "https", Region: "us-east-1", BucketLookup: minio.BucketLookupPath})
	if err != nil {
		return nil, err
	}
	bucket := os.Getenv("S3_BUCKET_UPLOADS")
	if bucket == "" {
		bucket = "vastu-raw-captures"
	}
	return &Store{client, bucket}, nil
}
func (s *Store) PutVerified(ctx context.Context, bucket, key, path, contentType string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	stat, err := f.Stat()
	if err != nil {
		return err
	}
	hash := sha256.New()
	if _, err = io.Copy(hash, f); err != nil {
		return err
	}
	expected := hex.EncodeToString(hash.Sum(nil))
	_, err = s.Client.FPutObject(ctx, bucket, key, path, minio.PutObjectOptions{ContentType: contentType, UserMetadata: map[string]string{"sha256": expected}})
	if err != nil {
		return err
	}
	info, err := s.Client.StatObject(ctx, bucket, key, minio.StatObjectOptions{})
	if err != nil {
		return err
	}
	if info.Size != stat.Size() {
		return errors.New("S3 object size mismatch")
	}
	object, err := s.Client.GetObject(ctx, bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return err
	}
	defer object.Close()
	actual := sha256.New()
	if _, err = io.Copy(actual, object); err != nil {
		return err
	}
	if !strings.EqualFold(expected, hex.EncodeToString(actual.Sum(nil))) {
		return errors.New("S3 object checksum mismatch")
	}
	return nil
}
