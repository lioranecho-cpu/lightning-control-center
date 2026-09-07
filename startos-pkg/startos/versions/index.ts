import { VersionGraph, VersionInfo } from '@start9labs/start-sdk'

const current = VersionInfo.of({
  version: '1.0.0:0',
  releaseNotes: 'Initial release',
  migrations: {},
})

export const versionGraph = VersionGraph.of({
  current,
  other: [],
})
