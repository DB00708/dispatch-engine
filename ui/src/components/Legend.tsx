export function Legend() {
  return (
    <ul className="legend" aria-label="Map legend">
      <li>
        <span className="lg-engineer" /> Engineer
      </li>
      <li>
        <span className="lg-engineer unused" /> Unused engineer
      </li>
      <li>
        <span className="lg-ticket p1" /> P1
      </li>
      <li>
        <span className="lg-ticket p2" /> P2
      </li>
      <li>
        <span className="lg-ticket p3" /> P3
      </li>
      <li>
        <span className="lg-ticket unassigned" /> Unassigned
      </li>
      <li>
        <span className="lg-line" /> Assignment
      </li>
      <li>
        <span className="lg-line tight" /> Tight (&lt; 15 min spare)
      </li>
    </ul>
  )
}
