import React from 'react';

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export default class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, fontFamily: 'monospace', fontSize: 14, color: '#333' }}>
          <h2 style={{ color: '#ff4d4f', marginBottom: 16 }}>页面渲染出错</h2>
          <div style={{ background: '#fff2f0', border: '1px solid #ffccc7', borderRadius: 6, padding: 16, marginBottom: 16 }}>
            <strong>Error: </strong>
            <span>{this.state.error?.message || 'Unknown error'}</span>
          </div>
          {this.state.error?.stack && (
            <details style={{ marginBottom: 16 }}>
              <summary style={{ cursor: 'pointer', marginBottom: 8 }}>Stack Trace</summary>
              <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, overflow: 'auto', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                {this.state.error.stack}
              </pre>
            </details>
          )}
          {this.state.errorInfo?.componentStack && (
            <details>
              <summary style={{ cursor: 'pointer', marginBottom: 8 }}>Component Stack</summary>
              <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, overflow: 'auto', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 16, padding: '8px 24px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            刷新页面
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
