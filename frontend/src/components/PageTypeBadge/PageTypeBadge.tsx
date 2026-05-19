import type { LucideIcon } from 'lucide-react';
import styles from './PageTypeBadge.module.css';

export type PageTypeBadgeVariant = 'offer' | 'search';

export interface PageTypeBadgeProps {
  icon: LucideIcon;
  label: string;
  variant: PageTypeBadgeVariant;
}

export default function PageTypeBadge({ icon: Icon, label, variant }: PageTypeBadgeProps) {
  return (
    <div className={`${styles.badge} ${styles[variant]}`}>
      <Icon size={12} aria-hidden />
      {label}
    </div>
  );
}
