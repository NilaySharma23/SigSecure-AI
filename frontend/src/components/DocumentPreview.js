import React from 'react';
import { Row, Col, Card, Button } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLock, faSearchPlus, faSearchMinus } from '@fortawesome/free-solid-svg-icons';

const DocumentPreview = ({ originalUrl, previewUrl, highlightOnly }) => {
  const [zoomLevel, setZoomLevel] = React.useState(100);  // Default 100%

  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 20, 200));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 20, 50));

  return (
    <Row className="preview-container mb-4">
      <Col md={6}>
        <Card>
          <Card.Header>
            Original Document
            <div style={{ float: 'right' }}>
              <Button variant="outline-secondary" size="sm" onClick={handleZoomIn}><FontAwesomeIcon icon={faSearchPlus} /></Button>
              <Button variant="outline-secondary" size="sm" onClick={handleZoomOut} className="ml-1"><FontAwesomeIcon icon={faSearchMinus} /></Button>
            </div>
          </Card.Header>
          <Card.Body style={{ overflow: 'auto', maxHeight: '600px' }}>
            {originalUrl && <iframe src={originalUrl} title="Original" width={`${zoomLevel}%`} height="500" style={{ border: 'none' }} />}
          </Card.Body>
        </Card>
      </Col>
      <Col md={6}>
        <Card>
          <Card.Header>
            {highlightOnly ? 'Highlighted Preview' : 'Protected Document'} <span className="secure-badge"><FontAwesomeIcon icon={faLock} /> Secure</span>
            <div style={{ float: 'right' }}>
              <Button variant="outline-secondary" size="sm" onClick={handleZoomIn}><FontAwesomeIcon icon={faSearchPlus} /></Button>
              <Button variant="outline-secondary" size="sm" onClick={handleZoomOut} className="ml-1"><FontAwesomeIcon icon={faSearchMinus} /></Button>
            </div>
          </Card.Header>
          <Card.Body style={{ overflow: 'auto', maxHeight: '600px' }}>
            {previewUrl && <iframe src={previewUrl} title="Preview/Redacted" width={`${zoomLevel}%`} height="500" style={{ border: 'none' }} />}
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};

export default DocumentPreview;