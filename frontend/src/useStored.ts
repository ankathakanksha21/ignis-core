import { useState } from 'react'

/** Read a value kept for this browser tab. Returns undefined when nothing usable is stored. */
export function readStored<T>(key: string): T | undefined {
  try {
    const raw = sessionStorage.getItem(key)
    return raw === null ? undefined : (JSON.parse(raw) as T)
  } catch {
    return undefined // storage is blocked or the value is not JSON: behave as if nothing was stored
  }
}

export function writeStored<T>(key: string, value: T): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    // storage is blocked: the page still works, it just forgets on leaving
  }
}

/**
 * useState that survives leaving the page and coming back, for as long as the tab is open.
 * `override` wins over what is stored, for a page opened from a link that carries its own values.
 */
export function useStored<T>(key: string, initial: T, override?: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    if (override !== undefined) {
      writeStored(key, override)
      return override
    }
    return readStored<T>(key) ?? initial
  })
  const store = (next: T) => {
    setValue(next)
    writeStored(key, next)
  }
  return [value, store]
}
