// Function to measure performance metrics (optional)
const reportWebVitals = onPerfEntry => {
  // Check if a function was passed in
  if (onPerfEntry && onPerfEntry instanceof Function) {
    // Dynamically import web-vitals functions
    import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
      // Call each metric and pass the reporting function
      getCLS(onPerfEntry);   // Cumulative Layout Shift
      getFID(onPerfEntry);   // First Input Delay
      getFCP(onPerfEntry);   // First Contentful Paint
      getLCP(onPerfEntry);   // Largest Contentful Paint
      getTTFB(onPerfEntry);  // Time to First Byte
    });
  }
};

// Export the function for use in index.js
export default reportWebVitals;
