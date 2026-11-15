import { setLevel, useLevel } from './level.ts'

/** Two buttons that switch every explanation between plain words and precise ones. The facts stay the same. */
export function LevelToggle() {
  const current = useLevel()
  return (
    <span className="voice-level" role="group" aria-label="Who the explanation is for">
      {(['student', 'researcher'] as const).map((name) => (
        <button key={name} type="button" className={name === current ? 'on' : ''} aria-pressed={name === current} onClick={() => setLevel(name)}>
          {name === 'student' ? 'Student' : 'Researcher'}
        </button>
      ))}
    </span>
  )
}
