import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import ErrorBanner from './ErrorBanner';
import styles from './ErrorBanner.module.css';

describe('ErrorBanner', () => {
  it('renders nothing when message is empty and there are no children', () => {
    expect(renderToStaticMarkup(<ErrorBanner message="" />)).toBe('');
    expect(renderToStaticMarkup(<ErrorBanner message="   " />)).toBe('');
  });

  it('renders message text with alert role by default', () => {
    const html = renderToStaticMarkup(<ErrorBanner message="שגיאה" />);
    expect(html).toContain('שגיאה');
    expect(html).toContain('role="alert"');
  });

  it('renders children after message', () => {
    const html = renderToStaticMarkup(
      <ErrorBanner message="קרה">
        <a href="/x">קישור</a>
      </ErrorBanner>
    );
    expect(html).toContain('קרה');
    expect(html).toContain('קישור');
  });

  it('renders children when message is whitespace-only', () => {
    const html = renderToStaticMarkup(<ErrorBanner message="  ">child</ErrorBanner>);
    expect(html).toContain('child');
  });

  it('applies compact variant class', () => {
    const html = renderToStaticMarkup(<ErrorBanner message="e" variant="compact" />);
    expect(html).toContain(styles.compact);
  });

  it('uses status role when passed', () => {
    const html = renderToStaticMarkup(<ErrorBanner message="x" role="status" />);
    expect(html).toContain('role="status"');
  });

  it('merges custom className', () => {
    const html = renderToStaticMarkup(<ErrorBanner message="m" className="extra" />);
    expect(html).toContain('extra');
  });
});
