package safego

import (
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestRecoverPanic_CatchesPanic(t *testing.T) {
	var wg sync.WaitGroup
	wg.Add(1)
	completed := false

	go func() {
		defer wg.Done()
		defer RecoverPanic("test", "TestCatchesPanic")
		panic("boom")
	}()

	wg.Wait()
	// If we get here, the panic was caught and didn't crash the test.
	completed = true
	assert.True(t, completed)
}

func TestRecoverPanic_NoPanic(t *testing.T) {
	// Should be a no-op when nothing panics.
	func() {
		defer RecoverPanic("test", "TestNoPanic")
	}()
}
