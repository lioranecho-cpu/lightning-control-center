import { sdk } from '../sdk'
import { storeJson } from '../fileModels/store.json'

export const seedFiles = sdk.setupOnInit(async (effects, kind) => {
  if (kind !== 'install') return

  await storeJson.merge(effects, {
    tier: 'community',
    licenseKey: '',
  })
})
