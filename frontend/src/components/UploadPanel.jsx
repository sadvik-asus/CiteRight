import { useRef, useState } from 'react';

export default function UploadPanel({ onFileSelect, fileName, disabled, isUploading }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onFileSelect(file);
  }

  return (
    <div
      className={`dropzone ${dragOver ? 'dropzone--over' : ''} ${disabled ? 'dropzone--disabled' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md"
        hidden
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileSelect(file);
        }}
      />
      {isUploading ? (
        <>
          <p className="dropzone-title">Processing document...</p>
          <p className="dropzone-hint">Extracting and chunking text, please wait</p>
        </>
      ) : fileName ? (
        <>
          <p className="dropzone-filename">{fileName}</p>
          <p className="dropzone-hint">indexed — click to replace</p>
        </>
      ) : (
        <>
          <p className="dropzone-title">Drop a source document</p>
          <p className="dropzone-hint">.pdf · .txt · .md — click or drag in</p>
        </>
      )}
    </div>
  );
}
