import { useState, type ReactNode } from 'react';
import styles from './HistorySection.module.css';

type Props = {
  title?: string;
  children: ReactNode;
  defaultOpen?: boolean;
};

export default function HistorySection({ title = 'היסטוריה', children, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={styles.wrap}>
      <button type="button" className={styles.toggle} onClick={() => setOpen((v) => !v)}>
        <span className={styles.toggleIcon} aria-hidden>
          {open ? '▾' : '▸'}
        </span>
        {title}
      </button>
      {open ? <div className={styles.body}>{children}</div> : null}
    </section>
  );
}
