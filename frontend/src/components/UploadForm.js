import React from 'react';
import { Form, Button, Row, Col, Tooltip, OverlayTrigger } from 'react-bootstrap';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faInfoCircle, faLock } from '@fortawesome/free-solid-svg-icons';

const UploadForm = ({ file, handleFileChange, privacyMode, setPrivacyMode, redactionStyle, setRedactionStyle, highlightOnly, setHighlightOnly, handleUpload, loading }) => {
  const renderTooltip = (text) => (
    <Tooltip>{text}</Tooltip>
  );

  return (
    <Form className="mb-4">
      <Row className="align-items-center">
        <Col md={4}>
          <Form.Group>
            <Form.Label>Upload PDF <FontAwesomeIcon icon={faLock} className="text-success" /></Form.Label>
            <Form.Control type="file" accept=".pdf" onChange={handleFileChange} />
          </Form.Group>
        </Col>
        <Col md={3}>
          <Form.Group>
            <Form.Label>Privacy Mode</Form.Label>
            <OverlayTrigger placement="top" overlay={renderTooltip('Choose how to protect signatures based on context.')}>
              <Form.Select value={privacyMode} onChange={(e) => setPrivacyMode(e.target.value)}>
                <option value="none">No Privacy</option>
                <option value="signer">Signer Privacy</option>
                <option value="witness">Witness Privacy</option>
                <option value="medical">Medical Mode</option>
              </Form.Select>
            </OverlayTrigger>
          </Form.Group>
        </Col>
        <Col md={3}>
          <Form.Group>
            <Form.Label>Redaction Style</Form.Label>
            <OverlayTrigger placement="top" overlay={renderTooltip('How to mask sensitive info.')}>
              <Form.Select value={redactionStyle} onChange={(e) => setRedactionStyle(e.target.value)}>
                <option value="black">Black Box</option>
                <option value="blur">Blur</option>
                <option value="watermark">Watermark</option>
              </Form.Select>
            </OverlayTrigger>
          </Form.Group>
        </Col>
        <Col md={2} className="d-flex align-items-end">
          <Form.Check 
            type="checkbox" 
            label="Highlight Only" 
            checked={highlightOnly} 
            onChange={(e) => setHighlightOnly(e.target.checked)} 
            className="mt-4"
          />
        </Col>
      </Row>
      <Button 
        variant="primary" 
        onClick={handleUpload} 
        disabled={loading || !file} 
        className="mt-3"
      >
        {loading ? 'Processing...' : 'Upload & Process'} <FontAwesomeIcon icon={faInfoCircle} />
      </Button>
    </Form>
  );
};

export default UploadForm;