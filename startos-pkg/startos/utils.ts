export const uiPort = 8765

// LND gRPC — passthrough TLS on Start9.
// TODO: verify hostId against the lnd-startos package (Start9Labs/lnd-startos/startos/utils).
export const lndGrpcHostId = 'grpc'
export const lndGrpcPort = 10009

// Bitcoin Core RPC — plaintext on the internal bridge.
// TODO: verify hostId against bitcoind-startos (Start9Labs/bitcoind-startos/startos/utils).
export const bitcoindRpcHostId = 'rpc'
export const bitcoindRpcPort = 8332
