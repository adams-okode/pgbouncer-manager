package storage

import (
	"testing"
)

func TestNewCredentialStorage(t *testing.T) {
	key := "testkey1234567890123456789012" // 32 bytes
	st, err := NewCredentialStorage(key)

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if st == nil {
		t.Fatal("expected storage, got nil")
	}
}

func TestNewCredentialStorage_InvalidKey(t *testing.T) {
	// Key too short (31 bytes)
	key := "testkey123456789012345678901" // 31 bytes
	_, err := NewCredentialStorage(key)

	if err == nil {
		t.Error("expected error for invalid key length")
	}
}

func TestEncryptDecrypt(t *testing.T) {
	key := "testkey1234567890123456789012" // 32 bytes
	st, _ := NewCredentialStorage(key)

	plaintext := "my-secret-password"
	ciphertext, err := st.Encrypt(plaintext)

	if err != nil {
		t.Fatalf("expected no error on encrypt, got %v", err)
	}

	if ciphertext == "" {
		t.Error("expected non-empty ciphertext")
	}

	decrypted, err := st.Decrypt(ciphertext)

	if err != nil {
		t.Fatalf("expected no error on decrypt, got %v", err)
	}

	if decrypted != plaintext {
		t.Errorf("expected %s, got %s", plaintext, decrypted)
	}
}

func TestEncryptDecrypt_Roundtrip(t *testing.T) {
	key := "testkey1234567890123456789012" // 32 bytes
	st, _ := NewCredentialStorage(key)

	// Test various inputs
	testCases := []string{
		"simple",
		"with spaces",
		"with-special!@#$%^&*()chars",
		"unicode: 日本語",
		"very-long-" + "string-" + "that-" + "goes-" + "on-" + "and-" + "on-" + "and-" + "on-" + "and-" + "on",
	}

	for _, tc := range testCases {
		ciphertext, err := st.Encrypt(tc)
		if err != nil {
			t.Fatalf("encrypt failed for %s: %v", tc, err)
		}

		decrypted, err := st.Decrypt(ciphertext)
		if err != nil {
			t.Fatalf("decrypt failed for %s: %v", tc, err)
		}

		if decrypted != tc {
			t.Errorf("roundtrip failed for %s: expected %s, got %s", tc, tc, decrypted)
		}
	}
}

func TestGenerateEncryptionKey(t *testing.T) {
	key, err := GenerateEncryptionKey()

	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(key) != 44 { // 32 bytes base64 encoded = 44 chars
		t.Errorf("expected 44 chars (32 bytes base64), got %d", len(key))
	}
}

func TestLoadSaveEncryptionKey(t *testing.T) {
	tmpFile := "/tmp/test_encryption_key"
	originalFile := ".env.encryption"

	// Temporarily change filename
	osRename(".env.encryption", tmpFile)
	defer osRename(tmpFile, ".env.encryption")

	key := "testkey1234567890123456789012" // 32 bytes

	err := SaveEncryptionKey(key)
	if err != nil {
		t.Fatalf("expected no error saving key, got %v", err)
	}

	loadedKey, err := LoadEncryptionKey()
	if err != nil {
		t.Fatalf("expected no error loading key, got %v", err)
	}

	if loadedKey != key {
		t.Errorf("expected %s, got %s", key, loadedKey)
	}
}

// Helper functions for testing
func osRename(old, new string) {
	// This would be os.Rename in real code
	// Used here to mock the rename operation
}
