package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// NodeConfig represents the persistent configuration for a node
type NodeConfig struct {
	NodeID         uint32            `json:"node_id"`
	CapnpAddr      string            `json:"capnp_addr"`
	LibP2PPort     int               `json:"libp2p_port"`
	UseLibP2P      bool              `json:"use_libp2p"`
	LocalMode      bool              `json:"local_mode"`
	BootstrapPeers []string          `json:"bootstrap_peers"`
	LastSavedAt    string            `json:"last_saved_at"`
	CustomSettings map[string]string `json:"custom_settings,omitempty"`
}

// ConfigManager handles loading and saving node configuration
type ConfigManager struct {
	configPath string
	config     *NodeConfig
	mu         sync.RWMutex
}

// NewConfigManager creates a new configuration manager
func NewConfigManager(nodeID uint32) *ConfigManager {
	// Determine config file path
	homeDir, err := os.UserHomeDir()
	if err != nil {
		log.Printf("⚠️  Could not get user home directory: %v", err)
		// Use temp directory as fallback for security
		homeDir = os.TempDir()
	}

	configDir := filepath.Join(homeDir, ".pangea")
	if err := os.MkdirAll(configDir, 0755); err != nil {
		log.Printf("⚠️  Could not create config directory: %v", err)
		// Use temp directory as final fallback
		configDir = os.TempDir()
	}

	configPath := filepath.Join(configDir, fmt.Sprintf("node_%d_config.json", nodeID))

	return &ConfigManager{
		configPath: configPath,
		config: &NodeConfig{
			NodeID:         nodeID,
			CustomSettings: make(map[string]string),
		},
	}
}

// LoadConfig loads configuration from disk, or returns default config if file doesn't exist
func (cm *ConfigManager) LoadConfig() (*NodeConfig, error) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// Check if config file exists
	if _, err := os.Stat(cm.configPath); os.IsNotExist(err) {
		log.Printf("📄 No existing config file found at %s, using defaults", cm.configPath)
		return cm.config, nil
	}

	// Read config file
	data, err := os.ReadFile(cm.configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	// Parse JSON
	if err := json.Unmarshal(data, cm.config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	log.Printf("✅ Loaded configuration from %s (last saved: %s)", cm.configPath, cm.config.LastSavedAt)
	return cm.config, nil
}

// SaveConfig saves current configuration to disk
func (cm *ConfigManager) SaveConfig(config *NodeConfig) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// Update timestamp with standardized format
	config.LastSavedAt = time.Now().Format(time.RFC3339)

	// Convert to JSON
	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	// Write to file
	if err := os.WriteFile(cm.configPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	cm.config = config
	log.Printf("✅ Saved configuration to %s", cm.configPath)
	return nil
}

// UpdateConfig updates a specific configuration value
func (cm *ConfigManager) UpdateConfig(key, value string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	if cm.config.CustomSettings == nil {
		cm.config.CustomSettings = make(map[string]string)
	}

	cm.config.CustomSettings[key] = value
	log.Printf("🔄 Updated config: %s = %s", key, value)
	return nil
}

// GetConfig returns a copy of the current configuration
func (cm *ConfigManager) GetConfig() *NodeConfig {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	// Return a copy to prevent external modification
	configCopy := *cm.config
	if cm.config.CustomSettings != nil {
		configCopy.CustomSettings = make(map[string]string)
		for k, v := range cm.config.CustomSettings {
			configCopy.CustomSettings[k] = v
		}
	}
	if cm.config.BootstrapPeers != nil {
		configCopy.BootstrapPeers = make([]string, len(cm.config.BootstrapPeers))
		copy(configCopy.BootstrapPeers, cm.config.BootstrapPeers)
	}

	return &configCopy
}

// AddBootstrapPeer adds a peer to the bootstrap list
func (cm *ConfigManager) AddBootstrapPeer(peerAddr string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	// Check for duplicates
	for _, existing := range cm.config.BootstrapPeers {
		if existing == peerAddr {
			return nil // Already exists
		}
	}

	cm.config.BootstrapPeers = append(cm.config.BootstrapPeers, peerAddr)
	log.Printf("➕ Added bootstrap peer: %s", peerAddr)
	return nil
}

// RemoveBootstrapPeer removes a peer from the bootstrap list
func (cm *ConfigManager) RemoveBootstrapPeer(peerAddr string) error {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	newList := make([]string, 0)
	found := false
	for _, existing := range cm.config.BootstrapPeers {
		if existing != peerAddr {
			newList = append(newList, existing)
		} else {
			found = true
		}
	}

	if found {
		cm.config.BootstrapPeers = newList
		log.Printf("➖ Removed bootstrap peer: %s", peerAddr)
	}

	return nil
}
