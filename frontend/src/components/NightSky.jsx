// Fixed starfield behind every screen. Positions are fixed so the sky never reshuffles.
const STARS = [
  [4, 8, 1.2], [11, 22, 0.8], [17, 5, 1], [23, 31, 0.7], [29, 12, 1.4], [36, 26, 0.8],
  [42, 6, 1], [48, 18, 0.7], [55, 9, 1.3], [61, 28, 0.8], [67, 4, 0.9], [73, 20, 1.1],
  [79, 11, 0.7], [85, 27, 1], [91, 7, 1.3], [96, 19, 0.8], [7, 38, 0.7], [33, 42, 0.9],
  [58, 40, 0.7], [88, 41, 0.9], [14, 55, 0.6], [46, 52, 0.6], [70, 50, 0.7], [94, 58, 0.6],
]

export function NightSky() {
  return (
    <svg className="night-sky" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      {STARS.map(([x, y, r]) => (
        <ellipse key={`${x}-${y}`} cx={x} cy={y} rx={r * 0.12} ry={r * 0.2} />
      ))}
    </svg>
  )
}
