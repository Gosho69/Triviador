export function Button({ variant = 'gold', pending = false, pendingLabel, disabled = false, children, className = '', ...rest }) {
  return (
    <button
      {...rest}
      className={`button button--${variant} ${className}`}
      aria-busy={pending || undefined}
      disabled={pending || disabled}
    >
      {pending && <span className="button__spinner" aria-hidden="true" />}
      <span>{pending && pendingLabel ? pendingLabel : children}</span>
    </button>
  )
}
