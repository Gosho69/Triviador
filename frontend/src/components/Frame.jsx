// Carved wood frame, gold trim, parchment surface.
export function Frame({ as: Tag = 'section', className = '', children, ...rest }) {
  return (
    <Tag className={`frame ${className}`} {...rest}>
      <span className="frame__stud frame__stud--tl" aria-hidden="true" />
      <span className="frame__stud frame__stud--tr" aria-hidden="true" />
      <span className="frame__stud frame__stud--bl" aria-hidden="true" />
      <span className="frame__stud frame__stud--br" aria-hidden="true" />
      <div className="frame__trim">
        <div className="frame__surface">{children}</div>
      </div>
    </Tag>
  )
}
