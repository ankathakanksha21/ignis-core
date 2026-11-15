import { useEffect } from 'react'

const APP = 'Flame in Freefall'

/** Names the browser tab after the open page. */
export function useTitle(page?: string | null) {
  useEffect(() => {
    document.title = page ? `${page} · ${APP}` : APP
  }, [page])
}
