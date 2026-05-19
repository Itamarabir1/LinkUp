/**
 * Sync i18n locale files from src (source of truth) to public (served at runtime).
 * Run via npm predev / prebuild — see package.json.
 */
import { cpSync, existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(__dirname, '..');
const srcLocales = join(frontendRoot, 'src', 'i18n', 'locales');
const publicLocales = join(frontendRoot, 'public', 'locales');

function collectJsonFiles(dir, base = dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectJsonFiles(full, base));
    } else if (entry.isFile() && entry.name.endsWith('.json')) {
      files.push(relative(base, full));
    }
  }
  return files.sort();
}

function syncLocales() {
  if (!existsSync(srcLocales)) {
    console.error(`[sync-locales] Source not found: ${srcLocales}`);
    process.exit(1);
  }

  mkdirSync(publicLocales, { recursive: true });

  const files = collectJsonFiles(srcLocales);
  if (files.length === 0) {
    console.warn('[sync-locales] No JSON files under src/i18n/locales');
    return;
  }

  console.log(`[sync-locales] ${srcLocales} → ${publicLocales}`);
  for (const rel of files) {
    const src = join(srcLocales, rel);
    const dest = join(publicLocales, rel);
    mkdirSync(dirname(dest), { recursive: true });
    cpSync(src, dest);
    console.log(`  synced ${rel.replace(/\\/g, '/')}`);
  }
  console.log(`[sync-locales] Done (${files.length} file(s)).`);
}

syncLocales();
