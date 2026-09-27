import { Button } from './Button'

export function LoadingScreen() {
  return (
    <div className="loading-screen" role="status">
      <span className="button__spinner button__spinner--large" aria-hidden="true" />
      <p>Opening the gates…</p>
    </div>
  )
}

export function UnavailableScreen({ onRetry }) {
  return (
    <div className="loading-screen" role="alert">
      <p>Can&apos;t reach the realm right now.</p>
      <p className="loading-screen__detail">The server did not answer. Check that it is running, then try again.</p>
      <Button onClick={onRetry}>Try again</Button>
    </div>
  )
}
