package errors

import (
	"errors"
	"fmt"
)

// AppError wraps domain/infrastructure failures for HTTP JSON aligned with LinkUp FastAPI.
type AppError struct {
	Code       string
	Message    string
	HTTPStatus int
	Err        error
}

func (e *AppError) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("%s: %v", e.Message, e.Err)
	}
	return e.Message
}

func (e *AppError) Unwrap() error {
	return e.Err
}

var (
	ErrConnection = &AppError{Code: "CHAT_WS_CONNECTION", Message: "שגיאת חיבור", HTTPStatus: 500}
	ErrAuth       = &AppError{Code: "CHAT_WS_AUTH", Message: "אימות נכשל", HTTPStatus: 401}
	ErrMessage    = &AppError{Code: "CHAT_WS_MESSAGE", Message: "שגיאת הודעה", HTTPStatus: 400}
	ErrPresence   = &AppError{Code: "CHAT_WS_PRESENCE", Message: "שגיאת נוכחות", HTTPStatus: 500}
)

// New builds an AppError with optional wrapped cause.
func New(code, message string, httpStatus int, err error) *AppError {
	return &AppError{Code: code, Message: message, HTTPStatus: httpStatus, Err: err}
}

// Wrap adds context to an error (fmt.Errorf %w).
func Wrap(err error, msg string) error {
	if err == nil {
		return nil
	}
	return fmt.Errorf("%s: %w", msg, err)
}

// Is reports whether target matches err in the chain.
func Is(err, target error) bool {
	return errors.Is(err, target)
}
