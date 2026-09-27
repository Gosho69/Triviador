import { KNIGHTS } from '../knights'
import { KnightCrest } from './KnightCrest'

export function AvatarPicker({ value, onChange, name = 'avatar_key', error }) {
  const messages = error ?? []

  return (
    <fieldset className="avatar-picker" aria-invalid={messages.length > 0 || undefined}>
      <legend className="field__label">Choose your knight</legend>
      <div className="avatar-picker__grid">
        {KNIGHTS.map((knight) => (
          <label key={knight.key} className="avatar-picker__option" data-colour={knight.colour}>
            <input
              type="radio"
              name={name}
              value={knight.key}
              checked={value === knight.key}
              onChange={() => onChange(knight.key)}
              className="visually-hidden"
            />
            <KnightCrest avatarKey={knight.key} size={52} title="" />
            <span className="avatar-picker__name">{knight.name}</span>
          </label>
        ))}
      </div>
      {messages.length > 0 && (
        <ul className="field__errors">
          {messages.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
    </fieldset>
  )
}
