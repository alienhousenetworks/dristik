import React from 'react';
import { ErrorState } from './ui';

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      const msg = String(this.state.error.message || '');
      const isChunkError =
        msg.includes('Importing a module script failed') ||
        msg.includes('Failed to fetch dynamically imported module') ||
        msg.includes('error loading dynamically imported module') ||
        msg.includes('Loading chunk');

      return (
        <ErrorState
          title={isChunkError ? "Application updated to a new version" : "This section failed to load"}
          description={
            isChunkError
              ? "A newer version of Dristik was deployed on the server. Please reload the page to load the latest components."
              : this.state.error.message
          }
          onRetry={() => {
            if (isChunkError) {
              window.location.reload();
            } else {
              this.setState({ error: null });
            }
          }}
        />
      );
    }
    return this.props.children;
  }
}
