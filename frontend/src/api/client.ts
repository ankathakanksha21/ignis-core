/** Calls the FastAPI backend. In development Vite proxies /api to :8000. */
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).catch(() => {
    throw new Error('the server is not answering. Start the backend and reload.')
  })
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} from /api${path}`)
  }
  return response.json() as Promise<T>
}
