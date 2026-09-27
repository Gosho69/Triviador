import { useId } from 'react'
import { ErrorGlyph } from './ErrorGlyph'

export function Field({ label, error, hint, ...inputProps }) {
  const id = useId()
  const messages = Array.isArray(error) ? error : error ? [error] : []
  const invalid = messages.length > 0
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = invalid ? `${id}-error` : undefined

  return (
    <div className="field" data-invalid={invalid || undefined}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="field__input"
        aria-invalid={invalid || undefined}
        aria-describedby={[errorId, hintId].filter(Boolean).join(' ') || undefined}
        {...inputProps}
      />
      {invalid && (
        <ul className="field__errors" id={errorId}>
          {messages.map((message) => (
            <li key={message}>
              <ErrorGlyph />
              {message}
            </li>
          ))}
        </ul>
      )}
      {hint && !invalid && (
        <p className="field__hint" id={hintId}>
          {hint}
        </p>
      )}
    </div>
  )
}
