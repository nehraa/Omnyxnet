@0x8ab89e4d39cbedac;

# Tensor representation for distributed computation
struct Tensor {
  shape @0 :List(UInt64);
  dtype @1 :DataType;
  data @2 :Data;
  # Serialized tensor data in the format specified by dtype
}

enum DataType {
  float32 @0;
  float64 @1;
  int32 @2;
  int64 @3;
  uint32 @4;
  uint64 @5;
}

# Training batch for distributed ML
struct TrainingBatch {
  batchId @0 :UInt64;
  samples @1 :List(Tensor);
  labels @2 :Tensor;
  metadata @3 :Text;
}

# Gradient update for distributed optimization
struct GradientUpdate {
  gradientId @0 :UInt64;
  gradients @1 :List(Tensor);
  loss @2 :Float64;
  timestamp @3 :UInt64;
  nodeId @4 :Text;
}

# RPC message wrapper
struct Message {
  messageId @0 :UInt64;
  messageType @1 :MessageType;
  sender @2 :Text;
  recipient @3 :Text;
  payload @4 :Data;
  timestamp @5 :UInt64;
}

enum MessageType {
  request @0;
  response @1;
  gradientSync @2;
  heartbeat @3;
}
