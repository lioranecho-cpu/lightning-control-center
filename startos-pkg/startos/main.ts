import { sdk } from './sdk'
import { uiPort, lndGrpcHostId, lndGrpcPort, bitcoindRpcHostId, bitcoindRpcPort } from './utils'
import { setInterfaces } from './interfaces'
import { setDependencies } from './dependencies'
import { seedFiles } from './init/seedFiles'

export const main = sdk.setupMain(async ({ effects, started }) => {
  const lndGrpcAddress = await sdk.host
    .getBridgeAddress(effects, {
      packageId: 'lnd',
      hostId: lndGrpcHostId,
      internalPort: lndGrpcPort,
      ssl: true,
    })
    .const()

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

  const daemons = sdk.Daemons.of(effects, started, [
    sdk.healthCheck.checkPortListening(effects, uiPort, {
      successMessage: 'LCC web interface is ready',
      errorMessage: 'LCC web interface is not responding',
    }),
  ])
    .addDaemon('main', {
      subcontainer: await sdk.SubContainer.of(effects, { imageId: 'main' }, 'lcc-main'),
      mounts,
      command: ['uvicorn', 'lcc_api:app', '--host', '0.0.0.0', '--port', String(uiPort)],
      env,
      ready: {
        display: 'Web Interface',
        fn: () =>
          sdk.healthCheck.checkPortListening(effects, uiPort, {
            successMessage: 'Ready',
            errorMessage: 'Starting…',
          }),
      },
    })

  return daemons.build()
})

export { setInterfaces, setDependencies, seedFiles }
