/**
 * Google Identity Services — module-level singleton.
 *
 * GIS is a document-level system: a single `<script>`, a single `window.google`,
 * and a single `initialize()` per clientId. Managing that lifecycle inside a
 * React effect breaks under StrictMode (double mount/cleanup) and also under
 * any parent re-render that changes effect dependency identity.
 *
 * This module owns the lifecycle once-per-page:
 *   - `loadScriptOnce()` is idempotent — repeated calls return the same Promise.
 *   - `ensureGisInitialized(clientId)` calls `google.accounts.id.initialize()`
 *     exactly once for the lifetime of the page (per clientId).
 *   - `setGisCredentialHandler(fn)` lets React adapters update the active
 *     credential handler without re-initializing GIS.
 *
 * Result: no double-init warnings, StrictMode-safe, and free of stale-closure
 * bugs that come from putting cross-component state inside hooks.
 */

import './googleIdentity';

const GIS_SRC = 'https://accounts.google.com/gsi/client';

let scriptPromise: Promise<void> | null = null;
let initializedClientId: string | null = null;
let credentialHandler: ((response: { credential: string }) => void) | null = null;

function loadScriptOnce(): Promise<void> {
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GIS_SRC}"]`
    );
    if (existing && window.google?.accounts?.id) {
      resolve();
      return;
    }
    const el = existing ?? document.createElement('script');
    if (!existing) {
      el.src = GIS_SRC;
      el.async = true;
      el.defer = true;
      document.head.appendChild(el);
    }
    el.addEventListener('load', () => {
      if (window.google?.accounts?.id) resolve();
      else reject(new Error('GIS API missing after script load'));
    });
    el.addEventListener('error', () =>
      reject(new Error('GIS script failed to load (likely 403 — origin not allowed)'))
    );
  });
  return scriptPromise;
}

/**
 * Idempotent. First call loads the script and calls `initialize()`; subsequent
 * calls (StrictMode double-mount, multiple GoogleSignIn instances, etc.)
 * return immediately without re-initializing.
 */
export async function ensureGisInitialized(clientId: string): Promise<void> {
  if (!clientId) throw new Error('VITE_GOOGLE_CLIENT_ID not set');
  await loadScriptOnce();
  if (initializedClientId === clientId) return;
  if (initializedClientId && initializedClientId !== clientId) {
    console.warn('[GSI] clientId changed mid-session; ignoring re-init');
    return;
  }
  window.google!.accounts.id.initialize({
    client_id: clientId,
    callback: (response) => credentialHandler?.(response),
    auto_select: false,
    cancel_on_tap_outside: true,
    itp_support: true,
  });
  initializedClientId = clientId;
  if (import.meta.env.DEV) {
    console.info(
      `[GSI] initialized once. clientId=${clientId.slice(0, 12)}… origin=${window.location.origin}`
    );
  }
}

/**
 * Register the function that receives the credential token. The active GIS
 * `initialize()` callback delegates to whatever handler is registered here,
 * so React adapters can swap handlers on every render without re-initializing.
 */
export function setGisCredentialHandler(
  handler: ((response: { credential: string }) => void) | null
): void {
  credentialHandler = handler;
}

export function getGisInitState(): {
  initialized: boolean;
  clientId: string | null;
} {
  return { initialized: initializedClientId !== null, clientId: initializedClientId };
}
