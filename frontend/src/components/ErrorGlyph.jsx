export function ErrorGlyph() {
  return (
    <svg className="error-glyph" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <path d="M8 1.5 15 14H1Z" fill="currentColor" />
      <path d="M8 6v3.6" stroke="var(--parchment-100)" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="8" cy="11.6" r="0.95" fill="var(--parchment-100)" />
    </svg>
  )
}
