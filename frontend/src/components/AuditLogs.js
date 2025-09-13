import React from 'react';
import { Accordion, ListGroup } from 'react-bootstrap';
const AuditLogs = ({ logs }) => {
  return (
    <Accordion defaultActiveKey="0" className="mt-4">
      <Accordion.Item eventKey="0">
        <Accordion.Header>Audit Logs (Compliance Summary)</Accordion.Header>
        <Accordion.Body style={{ maxHeight: '300px', overflowY: 'scroll' }}>
          <ListGroup>
            {logs.slice().reverse().map((log, i) => (
              <ListGroup.Item key={i}>
                <strong>{new Date(log.timestamp).toLocaleString()} - {log.file}</strong><br />
                Mode: {log.privacy_mode} | Style: {log.redaction_style}<br />
                Signatures: {log.signatures_detected} | Entities: {Object.entries(log.entities_redacted || {}).map(([k, v]) => `${k}: ${v}`).join(', ')}<br />
                Highlight: {log.highlight_only ? 'Yes' : 'No'}<br />
                {log.error && <span className="error-message">Error: {log.error}</span>}
              </ListGroup.Item>
            ))}
          </ListGroup>
        </Accordion.Body>
      </Accordion.Item>
    </Accordion>
  );
};
export default AuditLogs;