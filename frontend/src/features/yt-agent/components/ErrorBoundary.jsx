import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        // Update state so the next render will show the fallback UI.
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        // You can also log the error to an error reporting service
        console.error("Uncaught error:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            // Fallback UI
            return (
                <div className="error-boundary-fallback">
                    <div className="fallback-content">
                        <h1>Something went wrong</h1>
                        <p>The application encountered an unexpected error. Please try refreshing the page.</p>
                        <button
                            className="refresh-btn"
                            onClick={() => window.location.reload()}
                        >
                            Refresh Page
                        </button>
                        {process.env.NODE_ENV === 'development' && (
                            <details className="error-details">
                                <summary>Error Details</summary>
                                <pre>{this.state.error?.toString()}</pre>
                            </details>
                        )}
                    </div>
                    <style jsx>{`
            .error-boundary-fallback {
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
              width: 100vw;
              background-color: #f9fafb;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
              text-align: center;
              padding: 20px;
            }
            .fallback-content {
              max-width: 500px;
              background: white;
              padding: 40px;
              border-radius: 12px;
              box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }
            h1 {
              color: #111827;
              margin-bottom: 16px;
              font-size: 24px;
            }
            p {
              color: #4b5563;
              margin-bottom: 24px;
              line-height: 1.5;
            }
            .refresh-btn {
              background-color: #3b82f6;
              color: white;
              border: none;
              padding: 12px 24px;
              border-radius: 6px;
              font-weight: 600;
              cursor: pointer;
              transition: background-color 0.2s;
            }
            .refresh-btn:hover {
              background-color: #2563eb;
            }
            .error-details {
              margin-top: 24px;
              text-align: left;
            }
            .error-details summary {
              color: #9ca3af;
              cursor: pointer;
              font-size: 14px;
            }
            pre {
              background: #f3f4f6;
              padding: 12px;
              border-radius: 4px;
              font-size: 12px;
              overflow-x: auto;
              margin-top: 8px;
            }
          `}</style>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
