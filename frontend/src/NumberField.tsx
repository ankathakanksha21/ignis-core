import { useState } from 'react'

type Props = {
  value: number | null
  onCommit: (value: number | null) => void
  min: number
  max: number
  step: number | 'any'
  /** An empty box means "no value" and commits null. Without it an empty box commits nothing. */
  optional?: boolean
  placeholder?: string
  label?: string
}

/**
 * A number box that can be cleared and retyped. What is being typed is kept as
 * text, and only a number inside the range is passed on. Leaving the box with
 * something unusable in it puts the last good value back.
 */
export function NumberField({ value, onCommit, min, max, step, optional = false, placeholder, label }: Props) {
  const [draft, setDraft] = useState<string | null>(null)
  return (
    <input
      type="number"
      inputMode="decimal"
      min={min}
      max={max}
      step={step}
      placeholder={placeholder}
      aria-label={label}
      value={draft ?? (value === null ? '' : String(value))}
      onChange={(event) => {
        const text = event.target.value
        setDraft(text)
        if (text.trim() === '') {
          if (optional) onCommit(null)
          return
        }
        const typed = Number(text)
        if (Number.isFinite(typed) && typed >= min && typed <= max) onCommit(typed)
      }}
      onBlur={() => setDraft(null)}
    />
  )
}
