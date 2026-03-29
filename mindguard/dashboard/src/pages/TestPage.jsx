import React, { useEffect, useState } from 'react';

export default function TestPage() {
  const [apiStatus, setApiStatus] = useState('Testing...');
  const [wsStatus, setWsStatus] = useState('Not tested');

  const API_URL = process.env.REACT_APP_API_URL || 'https://nikhitha-nikhi12-mindguard-backend.hf.space';
  const WS_URL = process.env.REACT_APP_WS_URL || 'wss://nikhitha-nikhi12-mindguard-backend.hf.space/ws';

  useEffect(() => {
    console.log('Testing API connection...');
    console.log('API_URL:', API_URL);
    console.log('WS_URL:', WS_URL);

    fetch(`${API_URL}/health`)
      .then(res => res.json())
      .then(data => {
        console.log('API Response:', data);
        setApiStatus('✅ Connected: ' + JSON.stringify(data));
      })
      .catch(err => {
        console.error('API Error:', err);
        setApiStatus('❌ Failed: ' + err.message);
      });
  }, [API_URL]);

  return (
    <div style={{ padding: '20px', background: '#0a0b0e', color: '#fff', minHeight: '100vh' }}>
      <h1>MindGuard AI - Connection Test</h1>
      
      <div style={{ marginTop: '20px', padding: '20px', background: '#1a1c21', borderRadius: '8px' }}>
        <h2>Environment Variables</h2>
        <p><strong>REACT_APP_API_URL from env:</strong> {process.env.REACT_APP_API_URL || 'NOT SET'}</p>
        <p><strong>REACT_APP_WS_URL from env:</strong> {process.env.REACT_APP_WS_URL || 'NOT SET'}</p>
        <p><strong>API_URL (with fallback):</strong> {API_URL}</p>
        <p><strong>WS_URL (with fallback):</strong> {WS_URL}</p>
      </div>

      <div style={{ marginTop: '20px', padding: '20px', background: '#1a1c21', borderRadius: '8px' }}>
        <h2>API Connection Test</h2>
        <p><strong>Status:</strong> {apiStatus}</p>
        <p><strong>Endpoint:</strong> {API_URL}/health</p>
      </div>

      <div style={{ marginTop: '20px', padding: '20px', background: '#1a1c21', borderRadius: '8px' }}>
        <h2>WebSocket</h2>
        <p><strong>URL:</strong> {WS_URL}</p>
        <p><strong>Status:</strong> {wsStatus}</p>
      </div>

      <div style={{ marginTop: '20px' }}>
        <button 
          onClick={() => window.location.href = '/'}
          style={{ padding: '10px 20px', background: '#4A90E2', border: 'none', borderRadius: '4px', color: '#fff', cursor: 'pointer' }}
        >
          Back to App
        </button>
      </div>
    </div>
  );
}