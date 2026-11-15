/** The address that opens an experiment's page on the given table rows, as NASA published them. */
export function testLink(psiId: string, fileName: string, rows: number[]): string {
  const query = new URLSearchParams({ file: fileName, rows: rows.join(',') })
  return `/dashboard/${psiId}?${query}`
}
