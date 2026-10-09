// A stylised map of Bulgaria cut into territories, with three castles flying player flags.
const OUTLINE =
  'M70 70L112 108L150 158L212 170L300 164L390 180L470 170L560 176L640 160L702 150L762 128L820 104L880 70L930 92L962 150L940 202L952 262L930 330L960 400L936 452L960 502L872 520L800 502L740 492L680 510L610 520L560 506L480 530L400 520L320 540L250 560L200 522L170 462L130 402L100 332L120 272L80 212L60 150Z'

const BORDERS = [
  'M150 158L190 250L130 402',
  'M190 250L330 300L300 164',
  'M330 300L360 420L250 560',
  'M330 300L520 280L470 170',
  'M520 280L560 400L480 530',
  'M360 420L560 400',
  'M520 280L700 300L702 150',
  'M700 300L740 492',
  'M700 300L860 290L880 70',
  'M860 290L952 262',
  'M860 290L872 520',
  'M560 400L740 400',
]

const CASTLES = [
  { x: 205, y: 355, colour: 'crimson', label: 'Crimson castle' },
  { x: 560, y: 290, colour: 'azure', label: 'Azure castle' },
  { x: 800, y: 385, colour: 'verdant', label: 'Verdant castle' },
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
  return (
    <svg className="realm-map" viewBox="0 0 1020 640" role="img" aria-label="Map of the realm with three castles">
      <path d={OUTLINE} className="realm-map__shadow" transform="translate(0 14)" />
      <path d={OUTLINE} className="realm-map__land" />
      <g className="realm-map__borders">
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
