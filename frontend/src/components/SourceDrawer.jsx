const LEVEL_LABEL = {
  supported: 'Verified',
  weak: 'Weakly supported',
  unsupported: 'Unsupported',
};

export default function SourceDrawer({ claim, onClose }) {
  if (!claim) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside
        className="drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Source excerpt"
      >
        <div className="drawer-head">
          <span className={`proofmark proofmark--${claim.support_level}`}>
            {LEVEL_LABEL[claim.support_level] || claim.support_level}
          </span>
          <button className="drawer-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <p className="drawer-claim-label">Claim in the draft</p>
        <p className="drawer-claim">{claim.text}</p>

        <div className="drawer-rule" />

        <p className="drawer-claim-label">
          Source
          {claim.cited_source && (
            <span className="drawer-source-meta">
              {' '}— {claim.cited_source}
              {claim.cited_page ? `, p.${claim.cited_page}` : ''}
            </span>
          )}
        </p>

        {claim.cited_excerpt ? (
          <p className="drawer-excerpt">{claim.cited_excerpt}</p>
        ) : (
          <p className="drawer-excerpt drawer-excerpt--empty">
            No source was cited for this claim — that's exactly why it's flagged.
          </p>
        )}

        <div className="drawer-rule" />

        <p className="drawer-score">
          semantic match score <span className="mono">{claim.score.toFixed(3)}</span>
        </p>
      </aside>
    </div>
  );
}
