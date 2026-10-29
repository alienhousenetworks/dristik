import { lazy, ComponentType } from 'react';

/**
 * Resilient lazy loader for code-split components.
 * Automatically recovers from stale chunk errors (e.g. after a new Docker build or deployment)
 * by forcing a one-time clean page reload to fetch the latest assets.
 */
export function lazyWithRetry<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>
) {
  return lazy(async () => {
    const reloadKey = 'dristik_chunk_reload_' + window.location.pathname;
    const alreadyReloaded = sessionStorage.getItem(reloadKey);

    try {
      return await factory();
    } catch (error: any) {
      const msg = String(error?.message || '');
      const isImportFailure =
        msg.includes('Importing a module script failed') ||
        msg.includes('Failed to fetch dynamically imported module') ||
        msg.includes('error loading dynamically imported module') ||
        msg.includes('Loading chunk') ||
        error?.name === 'TypeError';

      if (isImportFailure && !alreadyReloaded) {
        sessionStorage.setItem(reloadKey, 'true');
        window.location.reload();
        // Return unresolved promise while page reloads
        return new Promise(() => {});
      }

      // If already reloaded and still failing, clear the flag and let ErrorBoundary handle it
      sessionStorage.removeItem(reloadKey);
      throw error;
    }
  });
}
