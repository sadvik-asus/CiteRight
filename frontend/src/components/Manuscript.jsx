export default function Manuscript({ claims, onCiteClick }) {
  return (
    <ul className="manuscript-points">
      {claims.map((claim, i) => (
        <li key={i} className="claim-item">
          {claim.text}{' '}
          <button
            className={`stamp stamp--${claim.support_level}`}
            onClick={() => onCiteClick(claim)}
            aria-label={`View source for claim ${i + 1}, ${claim.support_level}`}
            title={`${claim.support_level} · score ${claim.score.toFixed(2)}`}
          >
            {i + 1}
          </button>
        </li>
      ))}
    </ul>
  );
}
