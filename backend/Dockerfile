FROM golang:1.22-alpine AS builder

WORKDIR /app

ENV CGO_ENABLED=0

COPY go.mod go.sum ./
RUN go mod download

COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /vastu-server ./cmd/server

# Final runtime stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app
COPY --from=builder /vastu-server /app/vastu-server
RUN mkdir -p /app/uploads

EXPOSE 8080

CMD ["/app/vastu-server"]
