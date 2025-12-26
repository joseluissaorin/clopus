---
name: go-api
description: Go API development
version: 1.0.0
category: development
technologies: [go, gin, fiber, postgresql]
triggers:
  - go api
  - golang
  - gin
  - fiber
---

# Go API Development

High-performance Go API development.

## Capabilities

- RESTful API with Gin/Fiber/Chi
- Database with GORM or sqlx
- Authentication middleware
- Input validation
- Error handling patterns
- Graceful shutdown
- Configuration management
- Testing

## Project Structure

```
project/
├── cmd/
│   └── api/
│       └── main.go
├── internal/
│   ├── config/
│   ├── handlers/
│   ├── middleware/
│   ├── models/
│   ├── repository/
│   └── services/
├── pkg/
│   └── utils/
├── migrations/
├── go.mod
├── go.sum
└── Makefile
```

## Setup

```bash
# Initialize module
go mod init github.com/user/project

# Gin framework
go get -u github.com/gin-gonic/gin

# GORM
go get -u gorm.io/gorm
go get -u gorm.io/driver/postgres

# Validation
go get -u github.com/go-playground/validator/v10

# Configuration
go get -u github.com/spf13/viper
```

## Handler Pattern

```go
func (h *Handler) GetUser(c *gin.Context) {
    id := c.Param("id")

    user, err := h.service.GetUser(c.Request.Context(), id)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
        return
    }

    c.JSON(http.StatusOK, user)
}
```

## Best Practices

1. Use dependency injection
2. Separate business logic into services
3. Use context for cancellation
4. Implement proper error types
5. Use structured logging (zerolog/zap)
6. Write table-driven tests
7. Use golangci-lint
