package queue

import (
	"strings"

	"github.com/hibiken/asynq"
)

// ParseRedisConnOpt parses a Redis connection string or returns default client options.
// Supports full URIs (redis://[:password@]host:port[/db]) or plain addresses (host:port).
func ParseRedisConnOpt(redisAddrOrURL string, redisPassword ...string) asynq.RedisConnOpt {
	if redisAddrOrURL == "" {
		redisAddrOrURL = "localhost:6379"
	}

	// If it starts with a known Redis URI scheme, parse it via asynq.ParseRedisURI
	if strings.HasPrefix(redisAddrOrURL, "redis://") ||
		strings.HasPrefix(redisAddrOrURL, "rediss://") ||
		strings.HasPrefix(redisAddrOrURL, "redis-socket://") ||
		strings.HasPrefix(redisAddrOrURL, "redis-sentinel://") {
		opt, err := asynq.ParseRedisURI(redisAddrOrURL)
		if err == nil {
			return opt
		}
	}

	password := ""
	if len(redisPassword) > 0 {
		password = redisPassword[0]
	}

	return asynq.RedisClientOpt{
		Addr:     redisAddrOrURL,
		Password: password,
	}
}
