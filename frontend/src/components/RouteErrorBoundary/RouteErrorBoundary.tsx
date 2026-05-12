import * as Sentry from '@sentry/react';
import { Component, type ErrorInfo, type ReactNode } from 'react';
import styles from './RouteErrorBoundary.module.css';

interface Props {
  children: ReactNode;
  /** Resets error state whenever route path changes. */
  resetKey?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

const CHUNK_RELOAD_KEY = 'chunk_reload_attempted';

function isChunkLoadError(error: Error): boolean {
  return (
    error.name === 'ChunkLoadError' ||
    error.message.includes('Failed to fetch dynamically imported module') ||
    error.message.includes('Importing a module script failed') ||
    error.message.includes('Unable to preload CSS')
  );
}

export default class RouteErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    if (isChunkLoadError(error) && !sessionStorage.getItem(CHUNK_RELOAD_KEY)) {
      sessionStorage.setItem(CHUNK_RELOAD_KEY, '1');
      window.location.reload();
      return { hasError: false, error: null };
    }
    return { hasError: true, error };
  }

  componentDidMount() {
    sessionStorage.removeItem(CHUNK_RELOAD_KEY);
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[LinkUp] RouteErrorBoundary caught:', error, info.componentStack);
    if (import.meta.env.PROD) { Sentry.captureException(error); }
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  handleRetry = () => {
    if (this.state.error && isChunkLoadError(this.state.error)) {
      sessionStorage.removeItem(CHUNK_RELOAD_KEY);
      window.location.reload();
      return;
    }
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.wrap} role="alert">
          <h1 className={styles.title}>משהו השתבש</h1>
          <p className={styles.desc}>
            אירעה שגיאה בטעינת המסך. אפשר לנסות שוב או לחזור אחורה.
          </p>
          {import.meta.env.DEV && this.state.error?.message ? (
            <pre className={styles.pre}>{this.state.error.message}</pre>
          ) : null}
          <button type="button" className={styles.btn} onClick={this.handleRetry}>
            נסה שוב
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
