import { Component, type ErrorInfo, type ReactNode } from 'react';
import styles from './ChatErrorBoundary.module.css';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Error boundary for chat surfaces (thread / popup). RTL Hebrew fallback UI.
 */
export default class ChatErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, _info: ErrorInfo) {
    void _info;
    console.error('[LinkUp] ChatErrorBoundary caught:', error);
    // TODO: Sentry — remove when enabling in production
    // Chat crashes are critical — capture all
    // import * as Sentry from "@sentry/react";
    // if (import.meta.env.PROD) { Sentry.captureException(error); }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.wrap} role="alert">
          <h2 className={styles.title}>הצ׳אט זמנית לא זמין</h2>
          <p className={styles.desc}>אירעה שגיאה בתצוגת השיחה. נסה לרענן את הדף או לחזור לרשימת השיחות.</p>
        </div>
      );
    }
    return this.props.children;
  }
}
