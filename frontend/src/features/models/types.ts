// Shapes from ml/src/ignis_ml/contract.py, as served by /api/models and /api/predict.

export type Feature = {
  name: string
  kind: 'numeric' | 'categorical'
  unit: string | null
  tested_min: number | null
  tested_max: number | null
  categories: string[] | null
  source_column: string | null
}

export type ModelCard = {
  model_id: string
  title: string
  status: 'available' | 'not_implemented'
  fuel_class: string
  task: 'regression' | 'classification' | 'matcher'
  target: string
  target_unit: string | null
  classes: string[] | null
  features: Feature[]
  trained_on: { psi_id: string; file_name: string; doi: string | null; n_rows: number | null }[]
  evaluation: { name: string; value: number; baseline_name: string | null; baseline_value: number | null }[]
  cv_scheme: string | null
  notes: string | null
}

export type TestRef = { psi_id: string; file_name: string; row: number; doi: string | null; distance: number | null; values: Record<string, string> }

export type Prediction = {
  status: 'ok' | 'withheld' | 'invalid_input' | 'not_implemented'
  kind: string
  prediction: {
    value: number | null
    unit: string | null
    low: number | null
    high: number | null
    label: string | null
    class_probabilities: Record<string, number> | null
  } | null
  out_of_range: { feature: string; value: number | string; tested_min: number | null; tested_max: number | null; categories: string[] | null }[]
  nearest_tests: TestRef[]
  message: string | null
}
