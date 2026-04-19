import styles from './RouteArrow.module.css';

type Props = {
  className?: string;
};

/** Logical arrow U+2192 — mirrored visually in RTL via RouteArrow.module.css */
export default function RouteArrow({ className }: Props) {
  return (
    <span
      className={[styles.arrow, className].filter(Boolean).join(' ')}
      aria-hidden="true"
    >
      →
    </span>
  );
}
