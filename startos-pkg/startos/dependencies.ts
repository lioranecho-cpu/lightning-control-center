import { sdk } from './sdk'

export const setDependencies = sdk.setupDependencies(async ({ effects }) => {
  return {
    lnd: {
      kind: 'running' as const,
      versionRange: '>=0.17.0:0',
      healthChecks: [],
    },
  }
})
