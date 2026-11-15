// Row counts are shown in four steps of one blue, light to dark.
export const STEPS = [
  { from: 1, label: '1 to 4' },
  { from: 5, label: '5 to 19' },
  { from: 20, label: '20 to 59' },
  { from: 60, label: '60 or more' },
]

export const level = (rows: number) => STEPS.filter((step) => rows >= step.from).length
