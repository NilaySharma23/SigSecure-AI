// frontend/src/App.js
import React, { useState } from 'react';
import './App.css';
function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [originalUrl, setOriginalUrl] = useState(null);
  const [privacyMode, setPrivacyMode] = useState('none');
  const [redactionStyle, setRedactionStyle] = useState('black');
  const [highlightOnly, setHighlightOnly] = useState(false);  // New state
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const handleFileChange = (e) => setFile(e.target.files[0]);
  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('privacy_mode', privacyMode);
    formData.append('redaction_style', redactionStyle);
    formData.append('highlight_only', highlightOnly);  // New field
    try {
      const response = await fetch('http://localhost:5000/api/upload', { method: 'POST', body: formData });
      if (response.ok) {
        const blob = await response.blob();
        setPreviewUrl(URL.createObjectURL(blob));
        setOriginalUrl(URL.createObjectURL(file));
        fetchLogs();
      } else {
        const errData = await response.json();
        setError(errData.error || 'Upload failed');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    }
    setLoading(false);
  };
  const fetchLogs = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/audit_log');
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  };
  return (
    <div className="container">
      <h1>SigSecure AI</h1>
      <input type="file" onChange={handleFileChange} accept=".pdf" />
      <select value={privacyMode} onChange={(e) => setPrivacyMode(e.target.value)}>
        <option value="none">No Privacy</option>
        <option value="signer">Signer Privacy</option>
        <option value="witness">Witness Privacy</option>
        <option value="medical">Medical Mode</option>
      </select>
      <select value={redactionStyle} onChange={(e) => setRedactionStyle(e.target.value)}>
        <option value="black">Black Box</option>
        <option value="blur">Blur</option>
        <option value="watermark">Watermark</option>
      </select>
      <label>
        <input type="checkbox" checked={highlightOnly} onChange={(e) => setHighlightOnly(e.target.checked)} />
        Highlight Only (Preview Mode)
      </label>
      <button onClick={handleUpload} disabled={loading}>Upload & {highlightOnly ? 'Highlight' : 'Redact'}</button>
      {loading && <div>Loading...</div>}
      {error && <div className="error">{error}</div>}
      <div className="row">
        <div className="col">Original: {originalUrl && <iframe src={originalUrl} title="Original" width="100%" height="500" />}</div>
        <div className="col">{highlightOnly ? 'Preview' : 'Redacted'}: {previewUrl && <iframe src={previewUrl} title="Preview/Redacted" width="100%" height="500" />}</div>
      </div>
      <h2>Audit Logs</h2>
      <ul className="list-group">
        {logs.map((log, i) => (
          <li key={i} className="list-group-item">
            <strong>{log.timestamp} - {log.file} ({log.privacy_mode})</strong><br />
            Signatures: {log.signatures_detected}<br />
            Entities: {log.entities_redacted ? Object.entries(log.entities_redacted).map(([k,v]) => `${k}: ${v}`).join(', ') : 'None'}<br />
            Highlight Only: {log.highlight_only ? 'Yes' : 'No'}<br />
            {log.error && <span className="error">Error: {log.error}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
export default App; 