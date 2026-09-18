package events

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/segmentio/kafka-go"
)

// KafkaConfig holds broker and topic configuration for the Kafka producer.
type KafkaConfig struct {
	Brokers     []string
	TopicPrefix string // e.g. "vastu." → topic becomes "vastu.capture.created"
	Async       bool   // if true, writes are fire-and-forget (higher throughput, lower durability)
}

// KafkaProducer wraps a kafka-go writer to publish DomainEvents to Kafka.
// It mirrors the EventBus.Publish() signature so orchestrator code can
// switch between in-process and Kafka publishing transparently.
type KafkaProducer struct {
	writers map[string]*kafka.Writer // one writer per topic
	cfg     KafkaConfig
}

// NewKafkaProducer creates a KafkaProducer. Writers are created lazily per topic.
func NewKafkaProducer(cfg KafkaConfig) *KafkaProducer {
	return &KafkaProducer{
		writers: make(map[string]*kafka.Writer),
		cfg:     cfg,
	}
}

func (p *KafkaProducer) topicName(domainTopic string) string {
	if p.cfg.TopicPrefix == "" {
		return domainTopic
	}
	return p.cfg.TopicPrefix + domainTopic
}

func (p *KafkaProducer) writerFor(topic string) *kafka.Writer {
	if w, ok := p.writers[topic]; ok {
		return w
	}
	w := &kafka.Writer{
		Addr:                   kafka.TCP(p.cfg.Brokers...),
		Topic:                  p.topicName(topic),
		Balancer:               &kafka.LeastBytes{},
		WriteTimeout:           5 * time.Second,
		RequiredAcks:           kafka.RequireOne,
		AllowAutoTopicCreation: true,
	}
	p.writers[topic] = w
	return w
}

// PublishEvent serialises a DomainEvent to JSON and writes it to the matching Kafka topic.
// The Kafka message key is the correlationID (ensures same-correlation ordering).
func (p *KafkaProducer) PublishEvent(
	ctx context.Context,
	topic string,
	correlationID uuid.UUID,
	payload map[string]interface{},
) error {
	event := DomainEvent{
		ID:            uuid.New(),
		Topic:         topic,
		CorrelationID: correlationID,
		Payload:       payload,
		Timestamp:     time.Now().UTC(),
	}

	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("kafka_producer: failed to marshal event: %w", err)
	}

	msg := kafka.Message{
		Key:   []byte(correlationID.String()),
		Value: data,
		Headers: []kafka.Header{
			{Key: "event-topic", Value: []byte(topic)},
			{Key: "event-id", Value: []byte(event.ID.String())},
		},
	}

	w := p.writerFor(topic)
	if p.cfg.Async {
		// Non-blocking fire-and-forget
		go func() { _ = w.WriteMessages(context.Background(), msg) }()
		return nil
	}

	return w.WriteMessages(ctx, msg)
}

// Close flushes and closes all Kafka writers. Call on application shutdown.
func (p *KafkaProducer) Close() {
	for _, w := range p.writers {
		_ = w.Close()
	}
}
