package safego

import (
	"log/slog"
	"runtime/debug"
)

// RecoverPanic is a deferred helper that logs and absorbs panics
// so a single goroutine crash does not bring down the process.
func RecoverPanic(component, op string) {
	if r := recover(); r != nil {
		slog.Error("panic recovered",
			"component", component,
			"op", op,
			"error_code", "PANIC_RECOVERED",
			"panic", r,
			"stack", string(debug.Stack()),
		)
	}
}
