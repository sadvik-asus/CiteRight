const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchModes() {
  const res = await fetch(`${API_BASE}/modes`);
  return handle(res);
}

export async function uploadDocument(file, mode) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/documents/upload?mode=${mode}`, {
    method: 'POST',
    body: formData,
  });
  return handle(res);
}

export async function generateContent(documentId, query, mode) {
  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, query, mode }),
  });
  return handle(res);
}
