import { sdk } from '../sdk'
import { z } from 'zod'

const FileHelper = sdk.FileHelper

const shape = z.looseObject({
  tier: z.string().catch('community'),
  licenseKey: z.string().catch(''),
})

export type Store = z.infer<typeof shape>

export const storeJson = FileHelper.json(
  { base: sdk.volumes.main, subpath: '/store.json' },
  shape,
)
