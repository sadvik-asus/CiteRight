import { useEffect, useRef, useState } from 'react';

const UPLOAD_STEPS = [
  'reading document…',
  'splitting into chunks…',
  'embedding chunks (384-dim vectors)…',
  'indexed — ready to query',
];

const GENERATE_STEPS = (mode) => [
  'embedding query…',
  'searching vector index for relevant chunks…',
  `retrieved top matches — building ${mode} prompt…`,
  'calling LLM (grounded generation)…',
  'parsing claims + citation markers…',
  'verifying each claim against its cited source…',
  'computing trust score…',
];

export default function ProcessConsole({ kind, active, done, mode = 'general' }) {
  const steps = kind === 'upload' ? UPLOAD_STEPS : GENERATE_STEPS(mode);
  const [visibleCount, setVisibleCount] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!active) {
      setVisibleCount(0);
      return;
    }
    setVisibleCount(1);
    let i = 1;
    timerRef.current = setInterval(() => {
      i += 1;
      if (i >= steps.length) {
        clearInterval(timerRef.current);
        setVisibleCount(steps.length - 1); // hold on second-to-last until `done`
      } else {
        setVisibleCount(i);
      }
    }, 550);
    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, kind]);

  useEffect(() => {
    if (done) {
      clearInterval(timerRef.current);
      setVisibleCount(steps.length);
    }
  }, [done, steps.length]);

  if (!active) return null;

  return (
    <div className="console" role="status" aria-live="polite">
      <div className="console-titlebar">
        <span className="console-dot console-dot--r" />
        <span className="console-dot console-dot--y" />
        <span className="console-dot console-dot--g" />
        <span className="console-titlebar-label">citeright — pipeline</span>
      </div>
      <div className="console-body">
        {steps.slice(0, visibleCount).map((s, i) => {
          const isLast = i === visibleCount - 1;
          const isComplete = i < visibleCount - 1 || done;
          return (
            <div key={i} className="console-line">
              <span className={`console-marker ${isComplete ? 'console-marker--done' : ''}`}>
                {isComplete ? '✓' : '›'}
              </span>
              <span className="console-text">{s}</span>
              {isLast && !done && <span className="console-cursor">▌</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
