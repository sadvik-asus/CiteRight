import { useEffect, useState } from 'react';
import './App.css';
import ModeStamps from './components/ModeStamps';
import UploadPanel from './components/UploadPanel';
import Manuscript from './components/Manuscript';
import TrustLedger from './components/TrustLedger';
import SourceDrawer from './components/SourceDrawer';
import ProcessConsole from './components/ProcessConsole';
import { fetchModes, uploadDocument, generateContent } from './api';

const FALLBACK_MODES = [
  { id: 'general', label: 'General CiteRight', description: 'Turn any documents into a cited article or report.' },
  { id: 'study_notes', label: 'Study Notes', description: 'Turn lecture/textbook material into exam-ready notes.' },
  { id: 'research_summary', label: 'Research Summary', description: 'Turn papers into a cited literature review.' },
];

const CONSOLE_HOLD_MS = 650; // let the final checkmark sit visible before revealing the result

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function App() {
  const [modes, setModes] = useState(FALLBACK_MODES);
  const [mode, setMode] = useState('general');

  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadConsoleDone, setUploadConsoleDone] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const [query, setQuery] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genConsoleDone, setGenConsoleDone] = useState(false);
  const [genError, setGenError] = useState(null);
  const [result, setResult] = useState(null);

  const [activeClaim, setActiveClaim] = useState(null);

  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('citeright-theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('citeright-theme', theme);
  }, [theme]);

  useEffect(() => {
    fetchModes()
      .then((data) => data.length && setModes(data))
      .catch(() => {
        /* backend not reachable yet — keep fallback modes so the UI still renders */
      });
  }, []);

  async function handleFileSelect(f) {
    setFile(f);
    setDocumentId(null);
    setResult(null);
    setUploadError(null);
    setUploadConsoleDone(false);
    setUploading(true);
    try {
      const res = await uploadDocument(f, mode);
      setUploadConsoleDone(true);
      await wait(CONSOLE_HOLD_MS);
      setDocumentId(res.document_id);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleGenerate() {
    if (!documentId || !query.trim()) return;
    setGenerating(true);
    setGenConsoleDone(false);
    setGenError(null);
    setResult(null);
    try {
      const res = await generateContent(documentId, query.trim(), mode);
      setGenConsoleDone(true);
      await wait(CONSOLE_HOLD_MS);
      setResult(res);
    } catch (err) {
      setGenError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  const busy = uploading || generating;

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-title">
          <span className="masthead-mark">§</span>
          <div>
            <h1>CiteRight</h1>
            <p className="masthead-tagline">every claim, traced to its source</p>
          </div>
        </div>
        <div className="masthead-right">
          {result && (
            <span className="masthead-mode-tag">{modes.find((m) => m.id === mode)?.label}</span>
          )}
          <button
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            type="button"
          >
            {theme === 'dark' ? '☀' : '☾'}
          </button>
        </div>
      </header>

      <main className="layout">
        <section className="desk" aria-label="Controls">
          <h2 className="desk-heading">Source</h2>
          <UploadPanel onFileSelect={handleFileSelect} fileName={file?.name} disabled={busy} isUploading={uploading} />
          {uploading && <ProcessConsole kind="upload" active={uploading} done={uploadConsoleDone} />}
          {uploadError && <p className="status-line status-line--error">{uploadError}</p>}
          {documentId && !uploading && (
            <p className="status-line status-line--ok">ready — {documentId.slice(0, 8)}</p>
          )}

          <h2 className="desk-heading desk-heading--spaced">Mode</h2>
          <ModeStamps modes={modes} selected={mode} onSelect={setMode} disabled={busy} />

          <h2 className="desk-heading desk-heading--spaced">Request</h2>
          <textarea
            className="query-box"
            placeholder="What should the draft cover? e.g. Explain what RAG is and why chunk size matters."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={busy}
            rows={4}
          />
          <button
            className="generate-btn"
            onClick={handleGenerate}
            disabled={!documentId || !query.trim() || busy}
          >
            {generating ? 'Writing…' : 'Generate draft'}
          </button>
          {genError && <p className="status-line status-line--error">{genError}</p>}
        </section>

        <section className="paper-panel" aria-label="Generated draft">
          {!result && !generating && (
            <div className="empty-state">
              <p className="empty-state-mark">§</p>
              <p>Upload a source, choose a mode, and ask for a draft.</p>
              <p className="empty-state-sub">
                Every sentence in the result will carry a numbered stamp — click any
                stamp to see the exact passage it was grounded in.
              </p>
            </div>
          )}

          {generating && (
            <div className="empty-state">
              <p>Working on it…</p>
              <ProcessConsole kind="generate" active={generating} done={genConsoleDone} mode={mode} />
            </div>
          )}

          {result && (
            <>
              <TrustLedger claims={result.claims} trustScore={result.trust_score} backendUsed={result.backend_used} />
              <div className="manuscript-rule" />
              <Manuscript claims={result.claims} onCiteClick={setActiveClaim} />
            </>
          )}
        </section>
      </main>

      <footer className="app-footer">
        <p>Built by Vadla Sadvik Kumar</p>
        <div className="footer-links">
          <a href="https://github.com/sadvik-asus" target="_blank" rel="noreferrer" className="footer-link">
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
            GitHub
          </a>
          <a href="https://www.linkedin.com/in/sadvikkumar/" target="_blank" rel="noreferrer" className="footer-link">
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg>
            LinkedIn
          </a>
        </div>
      </footer>

      <SourceDrawer claim={activeClaim} onClose={() => setActiveClaim(null)} />
    </div>
  );
}
