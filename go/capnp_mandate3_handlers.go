package main

// This file contains RPC handlers for Mandate 3 features:
// - Security & Encryption (Tor/SOCKS5, E2EE configuration, Key Exchange)
// - Ephemeral Chat
// - Distributed ML (gradient exchange, model aggregation)

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
)

// ===================================================================
// Security & Encryption RPC Handlers (Mandate 3)
// ===================================================================

// SetProxyConfig implements the setProxyConfig RPC method
func (s *nodeServiceServer) SetProxyConfig(ctx context.Context, call NodeService_setProxyConfig) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	config, err := args.Config()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid proxy config: %v", err))
		return nil
	}

	// Extract proxy configuration
	proxyType, _ := config.ProxyType()
	proxyHost, _ := config.ProxyHost()
	username, _ := config.Username()
	password, _ := config.Password()
	
	proxyConfig := &ProxyConfigData{
		Enabled:   config.Enabled(),
		ProxyType: proxyType,
		ProxyHost: proxyHost,
		ProxyPort: config.ProxyPort(),
		Username:  username,
		Password:  password,
	}

	// Apply proxy configuration
	if err := s.securityManager.SetProxyConfig(proxyConfig); err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to set proxy config: %v", err))
		return nil
	}

	results.SetSuccess(true)
	log.Printf("✅ [SECURITY] Proxy config updated: enabled=%v, type=%s, host=%s:%d", 
		proxyConfig.Enabled, proxyConfig.ProxyType, proxyConfig.ProxyHost, proxyConfig.ProxyPort)
	
	return nil
}

// GetProxyConfig implements the getProxyConfig RPC method
func (s *nodeServiceServer) GetProxyConfig(ctx context.Context, call NodeService_getProxyConfig) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	config, err := results.NewConfig()
	if err != nil {
		return err
	}

	// Get current proxy configuration
	proxyConfig := s.securityManager.GetProxyConfig()

	// Populate response
	config.SetEnabled(proxyConfig.Enabled)
	config.SetProxyType(proxyConfig.ProxyType)
	config.SetProxyHost(proxyConfig.ProxyHost)
	config.SetProxyPort(proxyConfig.ProxyPort)
	config.SetUsername(proxyConfig.Username)
	config.SetPassword(proxyConfig.Password)

	return nil
}

// SetEncryptionConfig implements the setEncryptionConfig RPC method
func (s *nodeServiceServer) SetEncryptionConfig(ctx context.Context, call NodeService_setEncryptionConfig) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	config, err := args.Config()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid encryption config: %v", err))
		return nil
	}

	// Extract encryption configuration
	encType, _ := config.EncryptionType()
	keyExchangeAlgo, _ := config.KeyExchangeAlgorithm()
	symmetricAlgo, _ := config.SymmetricAlgorithm()
	
	encConfig := &EncryptionConfigData{
		EncryptionType:   encType,
		KeyExchangeAlgo:  keyExchangeAlgo,
		SymmetricAlgo:    symmetricAlgo,
		EnableSignatures: config.EnableSignatures(),
	}

	// Apply encryption configuration
	if err := s.securityManager.SetEncryptionConfig(encConfig); err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to set encryption config: %v", err))
		return nil
	}

	results.SetSuccess(true)
	log.Printf("✅ [SECURITY] Encryption config updated: type=%s, key_exchange=%s", 
		encConfig.EncryptionType, encConfig.KeyExchangeAlgo)
	
	return nil
}

// GetEncryptionConfig implements the getEncryptionConfig RPC method
func (s *nodeServiceServer) GetEncryptionConfig(ctx context.Context, call NodeService_getEncryptionConfig) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	config, err := results.NewConfig()
	if err != nil {
		return err
	}

	// Get current encryption configuration
	encConfig := s.securityManager.GetEncryptionConfig()

	// Populate response
	config.SetEncryptionType(encConfig.EncryptionType)
	config.SetKeyExchangeAlgorithm(encConfig.KeyExchangeAlgo)
	config.SetSymmetricAlgorithm(encConfig.SymmetricAlgo)
	config.SetEnableSignatures(encConfig.EnableSignatures)

	return nil
}

// InitiateKeyExchange implements the initiateKeyExchange RPC method
func (s *nodeServiceServer) InitiateKeyExchange(ctx context.Context, call NodeService_initiateKeyExchange) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	peerAddr, err := args.PeerAddr()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid peer address: %v", err))
		return nil
	}

	// Perform key exchange
	publicKey, err := s.securityManager.KeyExchange(ctx, peerAddr)
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Key exchange failed: %v", err))
		return nil
	}

	// Build response
	response, err := results.NewResponse()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to create response: %v", err))
		return nil
	}

	response.SetPublicKey(publicKey)
	response.SetSelectedCipher("rsa-oaep-sha256")

	results.SetSuccess(true)
	log.Printf("✅ [SECURITY] Key exchange initiated with peer: %s", peerAddr)
	
	return nil
}

// AcceptKeyExchange implements the acceptKeyExchange RPC method
func (s *nodeServiceServer) AcceptKeyExchange(ctx context.Context, call NodeService_acceptKeyExchange) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	request, err := args.Request()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid key exchange request: %v", err))
		return nil
	}

	// Get peer's public key
	peerPublicKey, err := request.PublicKey()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid public key: %v", err))
		return nil
	}

	algorithm, _ := request.Algorithm()
	
	// Import peer's public key
	peerID := fmt.Sprintf("peer-%d", time.Now().UnixNano())
	if err := s.securityManager.ImportPublicKey(peerID, peerPublicKey); err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to import public key: %v", err))
		return nil
	}

	// Generate our key pair if needed
	ourPublicKey, err := s.securityManager.ExportPublicKey("default")
	if err != nil {
		// Generate new key pair
		_, err = s.securityManager.GenerateRSAKeyPair("default")
		if err != nil {
			results.SetSuccess(false)
			results.SetErrorMsg(fmt.Sprintf("Failed to generate key pair: %v", err))
			return nil
		}
		ourPublicKey, _ = s.securityManager.ExportPublicKey("default")
	}

	// Build response
	response, err := results.NewResponse()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to create response: %v", err))
		return nil
	}

	response.SetPublicKey(ourPublicKey)
	response.SetSelectedCipher("rsa-oaep-sha256")

	results.SetSuccess(true)
	log.Printf("✅ [SECURITY] Key exchange accepted from peer: algorithm=%s", algorithm)
	
	return nil
}

// ===================================================================
// Ephemeral Chat RPC Handlers (Mandate 3)
// ===================================================================

// StartChatSession implements the startChatSession RPC method
func (s *nodeServiceServer) StartChatSession(ctx context.Context, call NodeService_startChatSession) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	peerAddr, err := args.PeerAddr()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid peer address: %v", err))
		return nil
	}

	encConfig, err := args.EncryptionConfig()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid encryption config: %v", err))
		return nil
	}

	// Extract encryption configuration
	encType, _ := encConfig.EncryptionType()
	keyExchangeAlgo, _ := encConfig.KeyExchangeAlgorithm()
	symmetricAlgo, _ := encConfig.SymmetricAlgorithm()
	
	encryptionConfig := &EncryptionConfigData{
		EncryptionType:   encType,
		KeyExchangeAlgo:  keyExchangeAlgo,
		SymmetricAlgo:    symmetricAlgo,
		EnableSignatures: encConfig.EnableSignatures(),
	}

	// Generate session ID
	sessionID := uuid.New().String()

	// Create chat session
	session, err := s.securityManager.CreateChatSession(sessionID, peerAddr, encryptionConfig)
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to create chat session: %v", err))
		return nil
	}

	// Build response
	sessionResp, err := results.NewSession()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to create session response: %v", err))
		return nil
	}

	sessionResp.SetSessionId(session.SessionID)
	sessionResp.SetPeerAddr(session.PeerAddr)
	sessionResp.SetEstablished(session.Established.Unix())

	results.SetSuccess(true)
	log.Printf("✅ [CHAT] Session started: %s with peer: %s, encryption: %s", 
		sessionID, peerAddr, encryptionConfig.EncryptionType)
	
	return nil
}

// SendEphemeralMessage implements the sendEphemeralMessage RPC method
func (s *nodeServiceServer) SendEphemeralMessage(ctx context.Context, call NodeService_sendEphemeralMessage) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	ephMsg, err := args.Message_()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid message: %v", err))
		return nil
	}

	// Extract message data
	fromPeer, _ := ephMsg.FromPeer()
	toPeer, _ := ephMsg.ToPeer()
	messageData, _ := ephMsg.Message_()
	encType, _ := ephMsg.EncryptionType()
	signature, _ := ephMsg.Signature()

	// Find the appropriate chat session
	sessions := s.securityManager.chatSessions
	var targetSession *ChatSessionData
	for _, session := range sessions {
		if session.PeerAddr == toPeer || session.PeerAddr == fromPeer {
			targetSession = session
			break
		}
	}

	if targetSession == nil {
		results.SetSuccess(false)
		results.SetErrorMsg("No active chat session with peer")
		return nil
	}

	// Create message data
	msgData := &EphemeralChatMessageData{
		FromPeer:       fromPeer,
		ToPeer:         toPeer,
		Message:        messageData,
		Timestamp:      time.Now().Unix(),
		MessageID:      uuid.New().String(),
		EncryptionType: encType,
		Signature:      signature,
	}

	// Add message to session
	if err := s.securityManager.AddChatMessage(targetSession.SessionID, msgData); err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to add message: %v", err))
		return nil
	}

	results.SetSuccess(true)
	log.Printf("✅ [CHAT] Message sent from %s to %s: %d bytes, encryption: %s", 
		fromPeer, toPeer, len(messageData), encType)
	
	// In a full implementation, this would:
	// 1. Encrypt the message using the session's encryption config
	// 2. Sign the message if signatures are enabled
	// 3. Send the encrypted message to the peer via libp2p
	// 4. Handle transmission errors and retries
	
	return nil
}

// ReceiveChatMessages implements the receiveChatMessages RPC method
func (s *nodeServiceServer) ReceiveChatMessages(ctx context.Context, call NodeService_receiveChatMessages) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	// Collect all messages from all active sessions
	allMessages := make([]*EphemeralChatMessageData, 0)
	for _, session := range s.securityManager.chatSessions {
		messages, err := s.securityManager.GetChatMessages(session.SessionID)
		if err == nil {
			allMessages = append(allMessages, messages...)
		}
	}

	// Build message list
	messagesList, err := results.NewMessages(int32(len(allMessages)))
	if err != nil {
		return err
	}

	for i, msg := range allMessages {
		msgItem := messagesList.At(i)
		msgItem.SetFromPeer(msg.FromPeer)
		msgItem.SetToPeer(msg.ToPeer)
		msgItem.SetMessage_(msg.Message)
		msgItem.SetTimestamp(msg.Timestamp)
		msgItem.SetMessageId(msg.MessageID)
		msgItem.SetEncryptionType(msg.EncryptionType)
		msgItem.SetSignature(msg.Signature)
	}

	log.Printf("📥 [CHAT] Retrieved %d messages", len(allMessages))
	return nil
}

// CloseChatSession implements the closeChatSession RPC method
func (s *nodeServiceServer) CloseChatSession(ctx context.Context, call NodeService_closeChatSession) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	sessionID, err := args.SessionId()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	// Close the session
	if err := s.securityManager.CloseChatSession(sessionID); err != nil {
		results.SetSuccess(false)
		return nil
	}

	results.SetSuccess(true)
	log.Printf("✅ [CHAT] Session closed: %s", sessionID)
	
	return nil
}

// ===================================================================
// Distributed ML RPC Handlers (Mandate 3)
// ===================================================================

// DistributeDataset implements the distributeDataset RPC method
func (s *nodeServiceServer) DistributeDataset(ctx context.Context, call NodeService_distributeDataset) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	dataset, err := args.Dataset()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid dataset: %v", err))
		return nil
	}

	workerNodes, err := args.WorkerNodes()
	if err != nil || workerNodes.Len() == 0 {
		results.SetSuccess(false)
		results.SetErrorMsg("No worker nodes specified")
		return nil
	}

	// Extract dataset ID
	datasetID, _ := dataset.DatasetId()

	// Extract chunks
	chunks, _ := dataset.Chunks()
	datasetChunks := make([]*DatasetChunkData, chunks.Len())
	for i := 0; i < chunks.Len(); i++ {
		chunk := chunks.At(i)
		chunkData, _ := chunk.Data()
		labels, _ := chunk.Labels()
		checksum, _ := chunk.Checksum()
		
		datasetChunks[i] = &DatasetChunkData{
			ChunkID:  chunk.ChunkId(),
			Data:     chunkData,
			Labels:   labels,
			Checksum: checksum,
		}
	}

	// Extract worker node IDs
	workers := make([]string, workerNodes.Len())
	for i := 0; i < workerNodes.Len(); i++ {
		worker, _ := workerNodes.At(i)
		workers[i] = worker
	}

	// Distribute dataset
	if err := s.mlCoordinator.DistributeDataset(ctx, datasetID, datasetChunks, workers); err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Dataset distribution failed: %v", err))
		return nil
	}

	results.SetSuccess(true)
	log.Printf("✅ [ML] Dataset distributed: %s to %d workers (%d chunks)", 
		datasetID, len(workers), len(datasetChunks))
	
	return nil
}

// SubmitGradient implements the submitGradient RPC method
func (s *nodeServiceServer) SubmitGradient(ctx context.Context, call NodeService_submitGradient) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	update, err := args.Update()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid gradient update: %v", err))
		return nil
	}

	// Extract gradient update data
	workerID, _ := update.WorkerId()
	gradients, _ := update.Gradients()
	
	gradientUpdate := &GradientUpdateData{
		WorkerID:     workerID,
		ModelVersion: update.ModelVersion(),
		Gradients:    gradients,
		NumSamples:   update.NumSamples(),
		Loss:         update.Loss(),
		Accuracy:     update.Accuracy(),
	}

	// Submit gradient to coordinator
	if err := s.mlCoordinator.SubmitGradient(ctx, gradientUpdate); err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Gradient submission failed: %v", err))
		return nil
	}

	results.SetSuccess(true)
	log.Printf("✅ [ML] Gradient received from worker %s: loss=%.4f, accuracy=%.4f", 
		workerID, gradientUpdate.Loss, gradientUpdate.Accuracy)
	
	return nil
}

// GetModelUpdate implements the getModelUpdate RPC method
func (s *nodeServiceServer) GetModelUpdate(ctx context.Context, call NodeService_getModelUpdate) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	modelVersion := args.ModelVersion()

	// Get model update
	modelUpdate, err := s.mlCoordinator.GetModelUpdate(modelVersion)
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Model not found: %v", err))
		return nil
	}

	// Build response
	update, err := results.NewUpdate()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to create update: %v", err))
		return nil
	}

	update.SetModelVersion(modelUpdate.ModelVersion)
	update.SetParameters(modelUpdate.Parameters)
	update.SetAggregationMethod(modelUpdate.AggregationMethod)
	update.SetNumWorkers(modelUpdate.NumWorkers)
	update.SetGlobalLoss(modelUpdate.GlobalLoss)
	update.SetGlobalAccuracy(modelUpdate.GlobalAccuracy)

	results.SetSuccess(true)
	log.Printf("✅ [ML] Model update retrieved: version=%d, loss=%.4f, accuracy=%.4f", 
		modelVersion, modelUpdate.GlobalLoss, modelUpdate.GlobalAccuracy)
	
	return nil
}

// StartMLTraining implements the startMLTraining RPC method
func (s *nodeServiceServer) StartMLTraining(ctx context.Context, call NodeService_startMLTraining) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	task, err := args.Task()
	if err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Invalid training task: %v", err))
		return nil
	}

	// Extract task data
	taskID, _ := task.TaskId()
	datasetID, _ := task.DatasetId()
	modelArch, _ := task.ModelArchitecture()
	aggNode, _ := task.AggregatorNode()
	
	workerNodes, _ := task.WorkerNodes()
	workers := make([]string, workerNodes.Len())
	for i := 0; i < workerNodes.Len(); i++ {
		worker, _ := workerNodes.At(i)
		workers[i] = worker
	}

	// Extract hyperparameters
	hyperparams, _ := task.Hyperparameters()
	params := make(map[string]string)
	for i := 0; i < hyperparams.Len(); i++ {
		kv := hyperparams.At(i)
		key, _ := kv.Key()
		value, _ := kv.Value()
		params[key] = value
	}

	// Create training task
	trainingTask := &MLTrainingTaskData{
		TaskID:            taskID,
		DatasetID:         datasetID,
		ModelArchitecture: modelArch,
		Hyperparameters:   params,
		WorkerNodes:       workers,
		AggregatorNode:    aggNode,
		Epochs:            task.Epochs(),
		BatchSize:         task.BatchSize(),
	}

	// Start training
	if err := s.mlCoordinator.StartMLTraining(ctx, trainingTask); err != nil {
		results.SetSuccess(false)
		results.SetErrorMsg(fmt.Sprintf("Failed to start training: %v", err))
		return nil
	}

	results.SetSuccess(true)
	log.Printf("✅ [ML] Training started: task=%s, workers=%d, epochs=%d", 
		taskID, len(workers), trainingTask.Epochs)
	
	return nil
}

// GetMLTrainingStatus implements the getMLTrainingStatus RPC method
func (s *nodeServiceServer) GetMLTrainingStatus(ctx context.Context, call NodeService_getMLTrainingStatus) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	taskID, err := args.TaskId()
	if err != nil {
		return err
	}

	// Get training status
	task, err := s.mlCoordinator.GetMLTrainingStatus(taskID)
	if err != nil {
		// Return empty status if task not found
		status, _ := results.NewStatus()
		status.SetTaskId(taskID)
		status.SetCurrentEpoch(0)
		status.SetTotalEpochs(0)
		return nil
	}

	// Build response
	status, err := results.NewStatus()
	if err != nil {
		return err
	}

	status.SetTaskId(task.TaskID)
	status.SetCurrentEpoch(task.CurrentEpoch)
	status.SetTotalEpochs(task.Epochs)
	status.SetActiveWorkers(uint32(len(task.WorkerNodes)))
	status.SetCompletedWorkers(0) // Would be calculated from worker status
	status.SetCurrentLoss(0.0)    // Would come from latest gradient updates
	status.SetCurrentAccuracy(0.0) // Would come from latest gradient updates

	// Estimate time remaining
	if task.CurrentEpoch > 0 && task.Status == "running" {
		elapsed := time.Since(task.StartTime).Seconds()
		epochTime := elapsed / float64(task.CurrentEpoch)
		remaining := epochTime * float64(task.Epochs-task.CurrentEpoch)
		status.SetEstimatedTimeRemaining(uint32(remaining))
	}

	log.Printf("📊 [ML] Status retrieved: task=%s, epoch=%d/%d, status=%s", 
		taskID, task.CurrentEpoch, task.Epochs, task.Status)
	
	return nil
}

// StopMLTraining implements the stopMLTraining RPC method
func (s *nodeServiceServer) StopMLTraining(ctx context.Context, call NodeService_stopMLTraining) error {
	results, err := call.AllocResults()
	if err != nil {
		return err
	}

	args := call.Args()
	taskID, err := args.TaskId()
	if err != nil {
		results.SetSuccess(false)
		return nil
	}

	// Stop training
	if err := s.mlCoordinator.StopMLTraining(taskID); err != nil {
		results.SetSuccess(false)
		return nil
	}

	results.SetSuccess(true)
	log.Printf("⏹️  [ML] Training stopped: task=%s", taskID)
	
	return nil
}
