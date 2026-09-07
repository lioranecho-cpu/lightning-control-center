import { i18n } from './i18n'
import { sdk } from './sdk'
import { uiPort } from './utils'

export const setInterfaces = sdk.setupInterfaces(async ({ effects }) => {
  const multi = sdk.MultiHost.of(effects, 'ui')
  const origin = await multi.bindPort(uiPort, {
    protocol: 'http',
    preferredExternalPort: uiPort,
  })

  const ui = sdk.createInterface(effects, {
    name: i18n('Web Interface'),
    id: 'ui',
    description: i18n('Lightning Control Center dashboard'),
    type: 'ui',
    masked: false,
    schemeOverride: null,
    username: null,
    path: '/dashboard',
    query: {},
  })

  return [await origin.export([ui])]
})
