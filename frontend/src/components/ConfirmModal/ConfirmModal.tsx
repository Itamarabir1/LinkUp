import { useEffect, useRef } from 'react';
import styles from './ConfirmModal.module.css';

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function getFocusableIn(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

export interface ConfirmModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  confirmLabel: string;
  cancelLabel?: string;
  variant?: 'danger' | 'primary';
  loading?: boolean;
  onConfirm: () => void | Promise<void>;
  /** Optional id for the title element (a11y) */
  titleId?: string;
}

export default function ConfirmModal({
  open,
  onClose,
  title,
  description,
  confirmLabel,
  cancelLabel = 'ביטול',
  variant = 'danger',
  loading = false,
  onConfirm,
  titleId = 'confirm-modal-title',
}: ConfirmModalProps) {
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  /** החזרת פוקוס כשסוגרים (לא תלוי ב-loading) */
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    return () => {
      previous?.focus?.();
    };
  }, [open]);

  /** מיקוד ראשוני / אחרי שינוי מצב loading */
  useEffect(() => {
    if (!open) return;
    const id = requestAnimationFrame(() => {
      const cancel = cancelButtonRef.current;
      if (cancel && !cancel.disabled) {
        cancel.focus();
      } else {
        panelRef.current?.focus();
      }
    });
    return () => cancelAnimationFrame(id);
  }, [open, loading]);

  useEffect(() => {
    if (!open) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading) onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, loading, onClose]);

  /** לכידת Tab בתוך המודאל */
  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    if (!panel) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const nodes = getFocusableIn(panel);
      if (nodes.length === 0) {
        e.preventDefault();
        return;
      }
      const { activeElement } = document;
      const inPanel = activeElement != null && panel.contains(activeElement);
      if (!inPanel) {
        e.preventDefault();
        (e.shiftKey ? nodes[nodes.length - 1] : nodes[0]).focus();
        return;
      }
      const i = nodes.indexOf(activeElement as HTMLElement);
      if (e.shiftKey) {
        if (i <= 0) {
          e.preventDefault();
          nodes[nodes.length - 1].focus();
        }
      } else if (i === -1 || i === nodes.length - 1) {
        e.preventDefault();
        nodes[0].focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, loading]);

  if (!open) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !loading) onClose();
  };

  const handleConfirm = async () => {
    await Promise.resolve(onConfirm());
  };

  return (
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={handleBackdropClick}
    >
      <div
        ref={panelRef}
        className={styles.box}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        {description && <p className={styles.desc}>{description}</p>}
        <div className={styles.actions}>
          <button
            ref={cancelButtonRef}
            type="button"
            className={styles.btnCancel}
            onClick={onClose}
            disabled={loading}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className={variant === 'danger' ? styles.btnDanger : styles.btnPrimary}
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading ? '...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
