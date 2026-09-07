import { sdk } from './sdk'
import { uiPort, lndGrpcHostId, lndGrpcPort, bitcoindRpcHostId, bitcoindRpcPort } from './utils'
import { setInterfaces } from './interfaces'
import { setDependencies } from './dependencies'
import { seedFiles } from './init/seedFiles'

export const main = sdk.setupMain(async ({ effects }) => {
  const lndGrpcAddressOrNull = await sdk.host
    .getBridgeAddress(effects, {
      packageId: 'lnd',
      hostId: lndGrpcHostId,
      internalPort: lndGrpcPort,
      ssl: true,
    })
    .const()

  if (!lndGrpcAddressOrNull) {
    throw new Error('LND gRPC bridge address is not available')
  }
  const lndGrpcAddress: string = lndGrpcAddressOrNull

  const maybeBtcAddress = await sdk.host
    .getBridgeAddress(effects, {
      packageId: 'bitcoind',
      hostId: bitcoindRpcHostId,
      internalPort: bitcoindRpcPort,
      ssl: false,
    })
    .once()
    .catch(() => null)

  const mounts = sdk.Mounts.of()
    .mountVolume({ volumeId: 'main', subpath: null, mountpoint: '/data', readonly: false })
    .mountDependency({
      dependencyId: 'lnd',
      volumeId: 'main',
      subpath: null,
      mountpoint: '/mnt/lnd',
      readonly: true,
    })

  if (maybeBtcAddress) {
    mounts.mountDependency({
      dependencyId: 'bitcoind',
      volumeId: 'main',
      subpath: null,
      mountpoint: '/mnt/bitcoind',
      readonly: true,
    })
  }

  const env: Record<string, string> = {
    START9_MODE: 'true',
    LND_GRPC_HOST: lndGrpcAddress,
    LND_MACAROON_PATH: '/mnt/lnd/data/chain/bitcoin/mainnet/admin.macaroon',
    LND_TLS_CERT_PATH: '/mnt/lnd/tls.cert',
    DATA_DIR: '/data',
  }

  if (maybeBtcAddress) {
    env['BTC_RPC_HOST'] = maybeBtcAddress
    env['BTC_COOKIE_PATH'] = '/mnt/bitcoind/.cookie'
  }

  const sub = sdk.SubContainer.of(effects, { imageId: 'main' }, mounts, 'lcc-main')

  return sdk.Daemons.of(effects)
    .addDaemon('main', {
      exec: { command: ['uvicorn', 'lcc_api:app', '--host', '0.0.0.0', '--port', String(uiPort)], env },
      subcontainer: sub,
      ready: {
        display: 'Web Interface',
        fn: async () => {
          const result = await sdk.healthCheck.checkPortListening(effects, uiPort, {
            successMessage: 'Ready',
            errorMessage: 'Starting…',
          })
          return result
        },
      },
      requires: [],
    })
    .build()
})

export { setInterfaces, setDependencies, seedFiles }
