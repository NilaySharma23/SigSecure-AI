import React from 'react';
import { Alert } from 'react-bootstrap';

const ErrorMessage = ({ error }) => error ? <Alert variant="danger" className="mt-3">{error}</Alert> : null;

export default ErrorMessage;