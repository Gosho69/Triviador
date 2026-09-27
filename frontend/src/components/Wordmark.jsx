export function Wordmark({ size = 'large', as: Tag = 'p' }) {
  return <Tag className={`wordmark wordmark--${size}`}>Triviador</Tag>
}
