import { useSyncExternalStore } from 'react'
import { readStored, writeStored } from '../../useStored.ts'

// Who the explanations are worded for. One choice for the whole app, kept for the tab.
export type Level = 'student' | 'researcher'

const KEY = 'voice.level'
const listeners = new Set<() => void>()
let level: Level = readStored<Level>(KEY) === 'researcher' ? 'researcher' : 'student'

export function setLevel(next: Level) {
  level = next
  writeStored(KEY, next)
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useLevel(): Level {
  return useSyncExternalStore(subscribe, () => level)
}
