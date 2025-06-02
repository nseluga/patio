// Import core React modules
import React from 'react';
import ReactDOM from 'react-dom/client';

// Import global styles and main App component
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Create root and render the app inside <div id="root">
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App /> {/* Render the main App component */}
  </React.StrictMode>
);

// Optional: Measure performance metrics (e.g. for analytics)
reportWebVitals();

// Debug message to confirm setup
console.log("Hello, JavaScript!");
