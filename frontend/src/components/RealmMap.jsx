import { useId } from 'react'

// Bulgaria's real outline (geoBoundaries ADM0, projected and simplified), cut into the game's
// three rows of six territories, with three castles flying player flags.
const OUTLINE =
  'M137 70L128 96L101 107L93 144L100 164L109 172L115 202L145 218L164 247L178 254L177 266L150 294L145 309L136 313L124 309L104 322L112 336L105 365L120 385L106 411L94 414L118 448L163 468L168 493L186 522L175 537L176 592L208 595L221 580L229 587L243 580L264 585L283 580L303 566L309 573L322 570L324 554L339 559L348 549L355 559L384 550L394 574L411 577L422 590L422 580L435 578L484 610L517 602L522 596L541 600L556 592L568 597L597 587L606 573L601 565L604 552L598 538L588 533L588 522L599 516L620 523L628 504L652 502L653 483L662 475L692 476L709 470L718 455L739 460L743 453L761 461L768 473L783 480L789 489L807 476L824 480L823 474L828 471L851 475L840 452L813 425L818 415L809 408L809 397L771 386L781 371L798 371L796 359L808 353L809 343L832 344L831 286L839 260L834 256L848 247L857 223L885 214L909 221L927 193L923 156L864 145L846 134L836 106L811 114L799 98L793 104L767 105L751 92L749 85L707 84L681 94L621 104L596 115L546 163L507 179L481 172L465 174L441 161L408 166L382 152L359 162L335 165L239 135L180 145L163 139L156 130L164 111L180 104L185 94Z'

// Drawn past the coast and clipped to the outline, so every line ends exactly at the border.
const BORDERS = [
  'M60 268L300 252L560 270L800 250L980 262',
  'M60 432L300 444L560 426L800 440L980 430',
  'M236 40L224 210L242 380L230 640',
  'M372 40L386 220L366 400L380 640',
  'M510 40L498 230L516 420L504 640',
  'M648 40L662 210L642 380L656 640',
  'M786 40L774 250L792 430L780 640',
]

// Near Sofia, Veliko Tarnovo and Burgas.
const CASTLES = [
  { x: 210, y: 345, colour: 'crimson', label: 'Crimson castle' },
  { x: 535, y: 305, colour: 'azure', label: 'Azure castle' },
  { x: 765, y: 350, colour: 'verdant', label: 'Verdant castle' },
]

export function Castle({ x, y, colour }) {
  return (
    <g className="castle" data-colour={colour} transform={`translate(${x} ${y})`}>
      <ellipse cx="0" cy="34" rx="46" ry="9" className="castle__shadow" />
      <path d="M-4 -58V-86" className="castle__pole" />
      <path d="M-4 -86L30 -78L-4 -69Z" className="castle__flag" />
      <path
        d="M-38 32V-6H-30V-14H-22V-6H-14V-14H-6V-6H2V-14H10V-6H18V-14H26V-6H34V-14H38V32Z"
        className="castle__wall"
      />
      <path d="M-18 -6V-50H-22V-58H-14V-52H-8V-58H0V-52H6V-58H14V-50H10V-6Z" className="castle__keep" />
      <path d="M-8 32V14C-8 8 8 8 8 14V32Z" className="castle__gate" />
      <rect x="-8" y="-36" width="6" height="10" rx="3" className="castle__gate" />
    </g>
  )
}

export function RealmMap() {
  const clipId = useId()
  return (
    <svg className="realm-map" viewBox="0 0 1020 640" role="img" aria-label="Map of Bulgaria with three castles">
      <defs>
        <clipPath id={clipId}>
          <path d={OUTLINE} />
        </clipPath>
      </defs>
      <path d={OUTLINE} className="realm-map__shadow" transform="translate(0 14)" />
      <path d={OUTLINE} className="realm-map__land" />
      <g className="realm-map__borders" clipPath={`url(#${clipId})`}>
        {BORDERS.map((d) => (
          <path key={d} d={d} />
        ))}
      </g>
      <path d={OUTLINE} className="realm-map__coast" />
      {CASTLES.map((castle) => (
        <Castle key={castle.colour} {...castle} />
      ))}
    </svg>
  )
}
