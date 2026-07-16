export default function TrustLedger({ claims, trustScore, backendUsed }) {
  const counts = claims.reduce(
    (acc, c) => {
      acc[c.support_level] = (acc[c.support_level] || 0) + 1;
      return acc;
    },
    { supported: 0, weak: 0, unsupported: 0 }
  );

  const pct = Math.round(trustScore * 100);

  return (
    <div className="ledger">
      <div className="ledger-score">
        <span className="ledger-score-number mono">{pct}</span>
        <span className="ledger-score-unit">%</span>
        <span className="ledger-score-label">trust score</span>
      </div>

      <div className="ledger-bar" aria-hidden="true">
        <div
          className="ledger-bar-fill ledger-bar-fill--supported"
          style={{ width: `${(counts.supported / claims.length) * 100}%` }}
        />
        <div
          className="ledger-bar-fill ledger-bar-fill--weak"
          style={{ width: `${(counts.weak / claims.length) * 100}%` }}
        />
        <div
          className="ledger-bar-fill ledger-bar-fill--unsupported"
          style={{ width: `${(counts.unsupported / claims.length) * 100}%` }}
        />
      </div>

      <div className="ledger-counts">
        <span className="ledger-count">
          <i className="dot dot--supported" /> {counts.supported} verified
        </span>
        <span className="ledger-count">
          <i className="dot dot--weak" /> {counts.weak} weak
        </span>
        <span className="ledger-count">
          <i className="dot dot--unsupported" /> {counts.unsupported} unsupported
        </span>
        {backendUsed === 'mock' && (
          <span className="ledger-mock-flag">mock generation — no live API key set</span>
        )}
      </div>
    </div>
  );
}
