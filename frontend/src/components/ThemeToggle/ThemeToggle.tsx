import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import styles from './ThemeToggle.module.css';

/** Theme toggle pinned in a corner (also visible on auth pages outside Layout). */
export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={styles.btn}
        onClick={toggleTheme}
        aria-label={isDark ? 'עבור למצב בהיר' : 'עבור למצב כהה'}
        title={isDark ? 'מצב בהיר' : 'מצב כהה'}
      >
        {isDark ? <Sun size={20} strokeWidth={2} aria-hidden /> : <Moon size={20} strokeWidth={2} aria-hidden />}
      </button>
    </div>
  );
}
