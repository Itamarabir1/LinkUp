import { Component, type ErrorInfo, type ReactNode } from 'react';
import styles from './RouteErrorBoundary.module.css';

interface Props {
  children: ReactNode;
  /** כשהנתיב משתנה – מאפס את מצב השגיאה */
  resetKey?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * תופס שגיאות רינדור בזרם הניתוב; מאפשר ניסיון חוזר בלי רענון מלא.
 */
export default class RouteErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[Linkup] RouteErrorBoundary caught:', error, info.componentStack);
    // TODO: Sentry — להסיר הערה כשעוברים לפרודקשן
    // קריסות boundary תמיד קריטיות — תפוס הכל
    // import * as Sentry from "@sentry/react";
    // if (import.meta.env.PROD) { Sentry.captureException(error); }
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  handleRetry = () => {
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
