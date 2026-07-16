export default function ModeStamps({ modes, selected, onSelect, disabled }) {
  return (
    <div className="mode-stamps">
      {modes.map((m) => (
        <button
          key={m.id}
          className={`mode-stamp ${selected === m.id ? 'mode-stamp--active' : ''}`}
          onClick={() => onSelect(m.id)}
          disabled={disabled}
          type="button"
        >
          <span className="mode-stamp-label">{m.label}</span>
          <span className="mode-stamp-desc">{m.description}</span>
        </button>
      ))}
    </div>
  );
}
