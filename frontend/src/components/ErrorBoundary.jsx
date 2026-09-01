import { Component } from 'react';
import { AlertOctagon, RotateCcw, Shield } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[TerraRisk Recovery Engine] Captured uncaught client exception:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleResetState = () => {
    try {
      localStorage.removeItem('terrarisk_token');
      localStorage.removeItem('terrarisk_user');
    } catch {
      // ignore
    }
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0B0F17',
          color: '#F8FAFC',
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", Inter, sans-serif',
          padding: '24px',
          boxSizing: 'border-box'
        }}>
          <div style={{
            maxWidth: '520px',
            width: '100%',
            background: 'rgba(23, 30, 44, 0.85)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '24px',
            padding: '32px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            textAlign: 'center',
            backdropFilter: 'blur(20px)'
          }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '20px',
              background: 'rgba(239, 68, 68, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              border: '1px solid rgba(239, 68, 68, 0.3)'
            }}>
              <AlertOctagon size={32} color="#EF4444" />
            </div>

            <h2 style={{ fontSize: '20px', fontWeight: '800', margin: '0 0 8px 0', letterSpacing: '-0.5px' }}>
              Interface Matrix Recovery
            </h2>
            <p style={{ fontSize: '13px', color: '#94A3B8', margin: '0 0 24px 0', lineHeight: 1.5 }}>
              A client render cycle encountered an unhandled exception. The recovery system caught the failure to preserve core telemetry stability.
            </p>

            {this.state.error && (
              <div style={{
                background: 'rgba(11, 15, 23, 0.7)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '12px',
                padding: '12px 16px',
                fontSize: '12px',
                color: '#EF4444',
                fontFamily: 'monospace',
                textAlign: 'left',
                marginBottom: '24px',
                overflowX: 'auto'
              }}>
                {this.state.error.toString()}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={this.handleReload}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: '#0A84FF',
                  color: '#FFF',
                  border: 'none',
                  borderRadius: '14px',
                  padding: '12px 20px',
                  fontWeight: '700',
                  fontSize: '13px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <RotateCcw size={15} /> Reload Interface
              </button>

              <button
                onClick={this.handleResetState}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: 'rgba(255, 255, 255, 0.08)',
                  color: '#94A3B8',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '14px',
                  padding: '12px 20px',
                  fontWeight: '700',
                  fontSize: '13px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <Shield size={15} /> Reset Auth & Reload
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
