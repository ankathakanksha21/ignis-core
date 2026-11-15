import { useEffect, useState } from 'react'
import { api } from './client.ts'

/** Fetch once per path. `data` stays undefined until the answer arrives. */
export function useApi<T>(path: string): { data?: T; error?: string } {
  const [state, setState] = useState<{ path: string; data?: T; error?: string }>({ path })

  useEffect(() => {
    let current = true
    api<T>(path).then(
      (data) => current && setState({ path, data }),
      (reason: Error) => current && setState({ path, error: reason.message }),
    )
    return () => {
      current = false
    }
  }, [path])

  return state.path === path ? state : {}
}
