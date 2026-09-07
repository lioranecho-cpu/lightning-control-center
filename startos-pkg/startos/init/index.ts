import { setDependencies } from '../dependencies'
import { setInterfaces } from '../interfaces'
import { sdk } from '../sdk'
import { versionGraph } from '../versions'
import { seedFiles } from './seedFiles'

export const init = sdk.setupInit(versionGraph, seedFiles, setInterfaces, setDependencies)

export const uninit = sdk.setupUninit(versionGraph)
