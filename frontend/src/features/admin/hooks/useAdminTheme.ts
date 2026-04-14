import { useSyncExternalStore } from 'react';

function subscribe(cb: () => void) {
  const mo = new MutationObserver(cb);
  mo.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  });
  return () => mo.disconnect();
}

function snapshot() {
  return document.documentElement.getAttribute('data-theme') === 'dark'
    ? 'dark'
    : 'light';
}

export function useAdminTheme() {
  const theme = useSyncExternalStore(subscribe, snapshot, () => 'light');
  const isDark = theme === 'dark';
  return {
    isDark,
    chart: isDark
      ? {
          axis: '#475569',
          grid: '#1e2535',
          tooltipBg: '#141924',
          tooltipBorder: '#2a3444',
          tooltipColor: '#e2e8f0',
        }
      : {
          axis: '#64748b',
          grid: '#e2e8f0',
          tooltipBg: '#ffffff',
          tooltipBorder: '#e2e8f0',
          tooltipColor: '#0f172a',
        },
  };
}
