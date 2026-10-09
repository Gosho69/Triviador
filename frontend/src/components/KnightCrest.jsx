import { useId } from 'react'
import { knightFor } from '../knights'

const SHIELD = 'M4 6H60V34C60 52 46 64 32 70C18 64 4 52 4 34Z'

// Each knight carries a different heraldic division so crests differ by shape, not only by colour.
const DIVISIONS = {
  'knight-1': 'M32 0H64V72H32Z',
  'knight-2': 'M0 52L32 30L64 52V72H0Z',
  'knight-3': 'M0 0H10L64 58V72H54L0 14Z',
  'knight-4': 'M32 0H64V36H32ZM0 36H32V72H0Z',
}

// `colour` overrides the knight's own colour, e.g. with a player's seat colour inside a game.
export function KnightCrest({ avatarKey, size = 64, title, colour }) {
  const clipId = useId()
  const knight = knightFor(avatarKey)
  const label = title ?? knight.name
  // An empty title marks the crest as decorative (a visible name sits next to it).
  const a11y = label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true }

  return (
    <svg
      className="crest"
      data-colour={colour ?? knight.colour}
      width={size}
      height={size * (72 / 64)}
      viewBox="0 0 64 72"
      {...a11y}
    >
      <defs>
        <clipPath id={clipId}>
          <path d={SHIELD} />
        </clipPath>
      </defs>
      <path d={SHIELD} className="crest__field" />
      <path d={DIVISIONS[knight.key]} className="crest__division" clipPath={`url(#${clipId})`} />
      <g className="crest__helm">
        <path d="M32 9C36 9 41 11 43 14C39 13 35 13.5 32 15Z" className="crest__plume" />
        <path d="M21 27C21 19 26 15 32 15C38 15 43 19 43 27V46H21Z" />
        <rect x="23.5" y="28" width="17" height="3.4" rx="1" className="crest__visor" />
        <path d="M32 31.4V46" className="crest__ridge" />
        <circle cx="27" cy="38" r="1.1" className="crest__visor" />
        <circle cx="37" cy="38" r="1.1" className="crest__visor" />
      </g>
      <path d={SHIELD} className="crest__trim" />
    </svg>
  )
}
