import { setupManifest } from '@start9labs/start-sdk'
import { short, long } from './i18n'

export const manifest = setupManifest({
  id: 'lightning-control-center',
  title: 'Lightning Control Center',
  license: 'MIT',
  packageRepo: 'https://github.com/lioranecho-cpu/lcc-startos',
  upstreamRepo: 'https://github.com/lioranecho-cpu/lightning-control-center',
  marketingUrl: 'https://satslist.shop',
  donationUrl: null,
  description: { short, long },
  volumes: ['main'],
  images: {
    main: {
      source: {
        dockerBuild: {},
      },
      arch: ['x86_64', 'aarch64'],
    },
  },
  dependencies: {
    lnd: {
      description: 'Required for Lightning node management — channels, payments, routing.',
      optional: false,
      s9pk: null,
    },
    bitcoind: {
      description: 'Provides mempool data and fee estimates.',
      optional: true,
      s9pk: null,
    },
  },
})
