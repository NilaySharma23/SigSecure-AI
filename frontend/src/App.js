import React, { useState, useEffect } from 'react';
import './App.css';
import UploadForm from './components/UploadForm';
import DocumentPreview from './components/DocumentPreview';
import AuditLogs from './components/AuditLogs';
import ErrorMessage from './components/ErrorMessage';
import { Modal, Button } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faShieldAlt } from '@fortawesome/free-solid-svg-icons';
import ClipLoader from 'react-spinners/ClipLoader';

function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [originalUrl, setOriginalUrl] = useState(null);
  const [privacyMode, setPrivacyMode] = useState('none');
  const [redactionStyle, setRedactionStyle] = useState('black');
  const [highlightOnly, setHighlightOnly] = useState(false);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [latestLog, setLatestLog] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setOriginalUrl(URL.createObjectURL(selectedFile));  // Create blob URL immediately
    } else {
      setOriginalUrl(null);  // Clear if no file
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('privacy_mode', privacyMode);
    formData.append('redaction_style', redactionStyle);
    formData.append('highlight_only', highlightOnly);
    try {
      const response = await fetch('http://localhost:5000/api/upload', { method: 'POST', body: formData });
      if (response.ok) {
        const blob = await response.blob();
        setPreviewUrl(URL.createObjectURL(blob));
        // Remove setOriginalUrl from here—it's now handled in handleFileChange
        fetchLogs();
        // Get the latest log
        const newLogs = await (await fetch('http://localhost:5000/api/audit_log')).json();
        const lastLog = newLogs[newLogs.length - 1];
        setLatestLog(lastLog);
        setShowSuccessModal(true);
      } else {
        const errData = await response.json();
        setError(errData.error || 'Upload failed');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    }
    setLoading(false);
  };

  const handleReset = () => {
    if (originalUrl) URL.revokeObjectURL(originalUrl);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setOriginalUrl(null);
    setError(null);
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

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="container mt-5">
      <h1 className="app-header">SigSecure AI <FontAwesomeIcon icon={faShieldAlt} className="text-primary" /></h1>
      <p className="text-center mb-4">Intelligent Signature Privacy – Protect What Matters, Preserve the Rest.</p>
      <UploadForm 
        file={file} 
        handleFileChange={handleFileChange} 
        privacyMode={privacyMode} 
        setPrivacyMode={setPrivacyMode} 
        redactionStyle={redactionStyle} 
        setRedactionStyle={setRedactionStyle} 
        highlightOnly={highlightOnly} 
        setHighlightOnly={setHighlightOnly} 
        handleUpload={handleUpload} 
        loading={loading} 
      />
      {loading && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(255,255,255,0.8)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <ClipLoader color="#007BFF" size={60} />
          <span style={{ marginLeft: '10px', fontSize: '1.2em' }}>Processing Document...</span>
        </div>
      )}
      <ErrorMessage error={error} />
      <Modal show={showSuccessModal} onHide={() => setShowSuccessModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Document Processed Successfully! <FontAwesomeIcon icon={faShieldAlt} className="text-success" /></Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Your document is protected with SigSecure AI.</p>
          {latestLog && (
            <>
              <strong>Quick Stats:</strong><br />
              Signatures Detected: {latestLog.signatures_detected}<br />
              Entities Protected: {Object.entries(latestLog.entities_redacted || {}).map(([k, v]) => `${k}: ${v}`).join(', ')}<br />
              Mode: {latestLog.privacy_mode}
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="primary" onClick={() => {
            const link = document.createElement('a');
            link.href = previewUrl;
            link.download = highlightOnly ? 'highlighted.pdf' : 'redacted.pdf';
            link.click();
          }}>
            Download Protected File
          </Button>
          <Button variant="secondary" onClick={() => setShowSuccessModal(false)}>Close</Button>
        </Modal.Footer>
      </Modal>
      <DocumentPreview originalUrl={originalUrl} previewUrl={previewUrl} highlightOnly={highlightOnly} />
      <AuditLogs logs={logs} />
      <Button variant="outline-danger" onClick={handleReset} className="mt-3">
        Reset
      </Button>
    </div>
  );
}

export default App;