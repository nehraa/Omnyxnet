package main

import (
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"log"
	"sync"
	"time"
)

// SecurityManager handles encryption configuration and key management
type SecurityManager struct {
	proxyConfig      *ProxyConfigData
	encryptionConfig *EncryptionConfigData
	keyPairs         map[string]*RSAKeyPair
	chatSessions     map[string]*ChatSessionData
	mu               sync.RWMutex
}

// ProxyConfigData holds SOCKS5/Tor proxy configuration
type ProxyConfigData struct {
	Enabled   bool
	ProxyType string // "socks5", "socks4", "http"
	ProxyHost string
	ProxyPort uint16
	Username  string
	Password  string
}

// EncryptionConfigData holds encryption configuration
type EncryptionConfigData struct {
	EncryptionType      string // "asymmetric", "symmetric", "none"
	KeyExchangeAlgo     string // "rsa", "ecc", "dh"
	SymmetricAlgo       string // "aes256", "chacha20"
	EnableSignatures    bool
}

// RSAKeyPair represents an RSA key pair for asymmetric encryption
type RSAKeyPair struct {
	PrivateKey *rsa.PrivateKey
	PublicKey  *rsa.PublicKey
	Created    time.Time
}

// ChatSessionData represents an active chat session
type ChatSessionData struct {
	SessionID        string
	PeerAddr         string
	EncryptionConfig *EncryptionConfigData
	PublicKey        []byte
	SessionKey       []byte
	Established      time.Time
	MessageQueue     []*EphemeralChatMessageData
}

// EphemeralChatMessageData represents a chat message
type EphemeralChatMessageData struct {
	FromPeer      string
	ToPeer        string
	Message       []byte
	Timestamp     int64
	MessageID     string
	EncryptionType string
	Signature     []byte
}

// NewSecurityManager creates a new security manager
func NewSecurityManager() *SecurityManager {
	return &SecurityManager{
		proxyConfig: &ProxyConfigData{
			Enabled:   false,
			ProxyType: "socks5",
		},
		encryptionConfig: &EncryptionConfigData{
			EncryptionType:   "asymmetric", // Default to asymmetric (Noise Protocol)
			KeyExchangeAlgo:  "curve25519",
			SymmetricAlgo:    "chacha20",
			EnableSignatures: true,
		},
		keyPairs:     make(map[string]*RSAKeyPair),
		chatSessions: make(map[string]*ChatSessionData),
	}
}

// SetProxyConfig updates the proxy configuration
func (sm *SecurityManager) SetProxyConfig(config *ProxyConfigData) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	
	sm.proxyConfig = config
	log.Printf("Proxy config updated: enabled=%v, type=%s, host=%s:%d", 
		config.Enabled, config.ProxyType, config.ProxyHost, config.ProxyPort)
	
	// Note: Actual proxy integration with libp2p would happen here
	// This requires configuring libp2p transport options
	// For full implementation, see: https://github.com/libp2p/go-libp2p/examples
	
	return nil
}

// GetProxyConfig returns the current proxy configuration
func (sm *SecurityManager) GetProxyConfig() *ProxyConfigData {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.proxyConfig
}

// SetEncryptionConfig updates the encryption configuration
func (sm *SecurityManager) SetEncryptionConfig(config *EncryptionConfigData) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	
	sm.encryptionConfig = config
	log.Printf("Encryption config updated: type=%s, key_exchange=%s, symmetric=%s", 
		config.EncryptionType, config.KeyExchangeAlgo, config.SymmetricAlgo)
	
	return nil
}

// GetEncryptionConfig returns the current encryption configuration
func (sm *SecurityManager) GetEncryptionConfig() *EncryptionConfigData {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.encryptionConfig
}

// GenerateRSAKeyPair generates a new RSA key pair for asymmetric encryption
func (sm *SecurityManager) GenerateRSAKeyPair(keyID string) (*RSAKeyPair, error) {
	// Generate 2048-bit RSA key pair
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, fmt.Errorf("failed to generate RSA key: %w", err)
	}
	
	keyPair := &RSAKeyPair{
		PrivateKey: privateKey,
		PublicKey:  &privateKey.PublicKey,
		Created:    time.Now(),
	}
	
	sm.mu.Lock()
	sm.keyPairs[keyID] = keyPair
	sm.mu.Unlock()
	
	log.Printf("Generated RSA key pair: %s", keyID)
	return keyPair, nil
}

// ExportPublicKey exports a public key in PEM format
func (sm *SecurityManager) ExportPublicKey(keyID string) ([]byte, error) {
	sm.mu.RLock()
	keyPair, exists := sm.keyPairs[keyID]
	sm.mu.RUnlock()
	
	if !exists {
		return nil, fmt.Errorf("key pair not found: %s", keyID)
	}
	
	publicKeyBytes, err := x509.MarshalPKIXPublicKey(keyPair.PublicKey)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal public key: %w", err)
	}
	
	publicKeyPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "RSA PUBLIC KEY",
		Bytes: publicKeyBytes,
	})
	
	return publicKeyPEM, nil
}

// ImportPublicKey imports a public key from PEM format
func (sm *SecurityManager) ImportPublicKey(keyID string, publicKeyPEM []byte) error {
	block, _ := pem.Decode(publicKeyPEM)
	if block == nil {
		return fmt.Errorf("failed to decode PEM block")
	}
	
	publicKey, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return fmt.Errorf("failed to parse public key: %w", err)
	}
	
	rsaPublicKey, ok := publicKey.(*rsa.PublicKey)
	if !ok {
		return fmt.Errorf("not an RSA public key")
	}
	
	keyPair := &RSAKeyPair{
		PublicKey: rsaPublicKey,
		Created:   time.Now(),
	}
	
	sm.mu.Lock()
	sm.keyPairs[keyID] = keyPair
	sm.mu.Unlock()
	
	log.Printf("Imported public key: %s", keyID)
	return nil
}

// EncryptWithPublicKey encrypts data with RSA public key
func (sm *SecurityManager) EncryptWithPublicKey(keyID string, plaintext []byte) ([]byte, error) {
	sm.mu.RLock()
	keyPair, exists := sm.keyPairs[keyID]
	sm.mu.RUnlock()
	
	if !exists || keyPair.PublicKey == nil {
		return nil, fmt.Errorf("public key not found: %s", keyID)
	}
	
	ciphertext, err := rsa.EncryptOAEP(sha256.New(), rand.Reader, keyPair.PublicKey, plaintext, nil)
	if err != nil {
		return nil, fmt.Errorf("encryption failed: %w", err)
	}
	
	return ciphertext, nil
}

// DecryptWithPrivateKey decrypts data with RSA private key
func (sm *SecurityManager) DecryptWithPrivateKey(keyID string, ciphertext []byte) ([]byte, error) {
	sm.mu.RLock()
	keyPair, exists := sm.keyPairs[keyID]
	sm.mu.RUnlock()
	
	if !exists || keyPair.PrivateKey == nil {
		return nil, fmt.Errorf("private key not found: %s", keyID)
	}
	
	plaintext, err := rsa.DecryptOAEP(sha256.New(), rand.Reader, keyPair.PrivateKey, ciphertext, nil)
	if err != nil {
		return nil, fmt.Errorf("decryption failed: %w", err)
	}
	
	return plaintext, nil
}

// SignMessage signs a message with RSA private key
func (sm *SecurityManager) SignMessage(keyID string, message []byte) ([]byte, error) {
	sm.mu.RLock()
	keyPair, exists := sm.keyPairs[keyID]
	sm.mu.RUnlock()
	
	if !exists || keyPair.PrivateKey == nil {
		return nil, fmt.Errorf("private key not found: %s", keyID)
	}
	
	hashed := sha256.Sum256(message)
	signature, err := rsa.SignPKCS1v15(rand.Reader, keyPair.PrivateKey, crypto.SHA256, hashed[:])
	if err != nil {
		return nil, fmt.Errorf("signing failed: %w", err)
	}
	
	return signature, nil
}

// VerifySignature verifies a message signature with RSA public key
func (sm *SecurityManager) VerifySignature(keyID string, message, signature []byte) error {
	sm.mu.RLock()
	keyPair, exists := sm.keyPairs[keyID]
	sm.mu.RUnlock()
	
	if !exists || keyPair.PublicKey == nil {
		return fmt.Errorf("public key not found: %s", keyID)
	}
	
	hashed := sha256.Sum256(message)
	err := rsa.VerifyPKCS1v15(keyPair.PublicKey, crypto.SHA256, hashed[:], signature)
	if err != nil {
		return fmt.Errorf("signature verification failed: %w", err)
	}
	
	return nil
}

// CreateChatSession creates a new ephemeral chat session
func (sm *SecurityManager) CreateChatSession(sessionID, peerAddr string, encConfig *EncryptionConfigData) (*ChatSessionData, error) {
	session := &ChatSessionData{
		SessionID:        sessionID,
		PeerAddr:         peerAddr,
		EncryptionConfig: encConfig,
		Established:      time.Now(),
		MessageQueue:     make([]*EphemeralChatMessageData, 0),
	}
	
	sm.mu.Lock()
	sm.chatSessions[sessionID] = session
	sm.mu.Unlock()
	
	log.Printf("Created chat session: %s with peer: %s", sessionID, peerAddr)
	return session, nil
}

// GetChatSession retrieves a chat session
func (sm *SecurityManager) GetChatSession(sessionID string) (*ChatSessionData, error) {
	sm.mu.RLock()
	session, exists := sm.chatSessions[sessionID]
	sm.mu.RUnlock()
	
	if !exists {
		return nil, fmt.Errorf("chat session not found: %s", sessionID)
	}
	
	return session, nil
}

// AddChatMessage adds a message to a chat session
func (sm *SecurityManager) AddChatMessage(sessionID string, message *EphemeralChatMessageData) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	
	session, exists := sm.chatSessions[sessionID]
	if !exists {
		return fmt.Errorf("chat session not found: %s", sessionID)
	}
	
	session.MessageQueue = append(session.MessageQueue, message)
	log.Printf("Added message to session %s: %s", sessionID, message.MessageID)
	
	return nil
}

// GetChatMessages retrieves messages from a chat session
func (sm *SecurityManager) GetChatMessages(sessionID string) ([]*EphemeralChatMessageData, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	
	session, exists := sm.chatSessions[sessionID]
	if !exists {
		return nil, fmt.Errorf("chat session not found: %s", sessionID)
	}
	
	// Return copy of messages and clear queue
	messages := make([]*EphemeralChatMessageData, len(session.MessageQueue))
	copy(messages, session.MessageQueue)
	session.MessageQueue = make([]*EphemeralChatMessageData, 0)
	
	return messages, nil
}

// CloseChatSession closes a chat session
func (sm *SecurityManager) CloseChatSession(sessionID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	
	delete(sm.chatSessions, sessionID)
	log.Printf("Closed chat session: %s", sessionID)
	
	return nil
}

// KeyExchange performs key exchange with a peer
func (sm *SecurityManager) KeyExchange(ctx context.Context, peerAddr string) ([]byte, error) {
	// Generate or retrieve key pair
	_, exists := sm.keyPairs["default"]
	if !exists {
		_, err := sm.GenerateRSAKeyPair("default")
		if err != nil {
			return nil, fmt.Errorf("failed to generate key pair: %w", err)
		}
	}
	
	// Export public key
	publicKeyPEM, err := sm.ExportPublicKey("default")
	if err != nil {
		return nil, fmt.Errorf("failed to export public key: %w", err)
	}
	
	log.Printf("Performing key exchange with peer: %s", peerAddr)
	
	// In a full implementation, this would:
	// 1. Send our public key to the peer
	// 2. Receive peer's public key
	// 3. Optionally generate and exchange a symmetric session key
	// 4. Verify signatures if enabled
	
	return publicKeyPEM, nil
}
