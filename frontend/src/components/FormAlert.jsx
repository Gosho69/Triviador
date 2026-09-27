import { ErrorGlyph } from './ErrorGlyph'

// Errors that belong to the whole form rather than one field.
export function FormAlert({ errors }) {
  const messages = [...(errors?.non_field_errors ?? []), ...(errors?.detail ?? [])]
  if (messages.length === 0) return null

  return (
    <div className="form-alert" role="alert">
      <ErrorGlyph />
      <div>
        {messages.map((message) => (
          <p key={message}>{message}</p>
        ))}
      </div>
    </div>
  )
}
