import path from "path";
import { readFileSync, existsSync, statSync, writeFileSync } from "fs";
import { exec } from "child_process";
import { logger } from "../utils/logger.js";
import { HOOK_TIMEOUTS, getTimeout } from "./hook-constants.js";
import { SettingsDefaultsManager } from "./SettingsDefaultsManager.js";
import { MARKETPLACE_ROOT, USER_SETTINGS_PATH } from "./paths.js";

// Named constants for health checks
// Allow env var override for users on slow systems (e.g., CLAUDE_MEM_HEALTH_TIMEOUT_MS=10000)
const HEALTH_CHECK_TIMEOUT_MS = (() => {
  const envVal = process.env.CLAUDE_MEM_HEALTH_TIMEOUT_MS;
  if (envVal) {
    const parsed = parseInt(envVal, 10);
    if (Number.isFinite(parsed) && parsed >= 500 && parsed <= 300000) {
      return parsed;
    }
    // Invalid env var — log once and use default
    logger.warn('SYSTEM', 'Invalid CLAUDE_MEM_HEALTH_TIMEOUT_MS, using default', {
      value: envVal, min: 500, max: 300000
    });
  }
  return getTimeout(HOOK_TIMEOUTS.HEALTH_CHECK);
})();

/**
 * Fetch with a timeout using Promise.race instead of AbortSignal.
 * AbortSignal.timeout() causes a libuv assertion crash in Bun on Windows,
 * so we use a racing setTimeout pattern that avoids signal cleanup entirely.
 * The orphaned fetch is harmless since the process exits shortly after.
 */
export function fetchWithTimeout(url: string, init: RequestInit = {}, timeoutMs: number): Promise<Response> {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(
      () => reject(new Error(`Request timed out after ${timeoutMs}ms`)),
      timeoutMs
    );
    fetch(url, init).then(
      response => { clearTimeout(timeoutId); resolve(response); },
      err => { clearTimeout(timeoutId); reject(err); }
    );
  });
}

// Cache to avoid repeated settings file reads
let cachedPort: number | null = null;
let cachedHost: string | null = null;

/**
 * Get the worker port number from settings
 * Uses CLAUDE_MEM_WORKER_PORT from settings file or default (37777)
 * Caches the port value to avoid repeated file reads
 */
export function getWorkerPort(): number {
  if (cachedPort !== null) {
    return cachedPort;
  }

  const settingsPath = path.join(SettingsDefaultsManager.get('CLAUDE_MEM_DATA_DIR'), 'settings.json');
  const settings = SettingsDefaultsManager.loadFromFile(settingsPath);
  cachedPort = parseInt(settings.CLAUDE_MEM_WORKER_PORT, 10);
  return cachedPort;
}

/**
 * Get the worker host address
 * Uses CLAUDE_MEM_WORKER_HOST from settings file or default (127.0.0.1)
 * Caches the host value to avoid repeated file reads
 */
export function getWorkerHost(): string {
  if (cachedHost !== null) {
    return cachedHost;
  }

  const settingsPath = path.join(SettingsDefaultsManager.get('CLAUDE_MEM_DATA_DIR'), 'settings.json');
  const settings = SettingsDefaultsManager.loadFromFile(settingsPath);
  cachedHost = settings.CLAUDE_MEM_WORKER_HOST;
  return cachedHost;
}

/**
 * Clear the cached port and host values.
 * Call this when settings are updated to force re-reading from file.
 */
export function clearPortCache(): void {
  cachedPort = null;
  cachedHost = null;
}

/**
 * Build a full URL for a given API path.
 */
export function buildWorkerUrl(apiPath: string): string {
  return `http://${getWorkerHost()}:${getWorkerPort()}${apiPath}`;
}

/**
 * Make an HTTP request to the worker over TCP.
 *
 * This is the preferred way for hooks to communicate with the worker.
 */
export function workerHttpRequest(
  apiPath: string,
  options: {
    method?: string;
    headers?: Record<string, string>;
    body?: string;
    timeoutMs?: number;
  } = {}
): Promise<Response> {
  const method = options.method ?? 'GET';
  const timeoutMs = options.timeoutMs ?? HEALTH_CHECK_TIMEOUT_MS;

  const url = buildWorkerUrl(apiPath);
  const init: RequestInit = { method };
  if (options.headers) {
    init.headers = options.headers;
  }
  if (options.body) {
    init.body = options.body;
  }

  if (timeoutMs > 0) {
    return fetchWithTimeout(url, init, timeoutMs);
  }
  return fetch(url, init);
}

/**
 * Check if worker HTTP server is responsive.
 * Uses /api/health (liveness) instead of /api/readiness because:
 * - Hooks have 15-second timeout, but full initialization can take 5+ minutes (MCP connection)
 * - /api/health returns 200 as soon as HTTP server is up (sufficient for hook communication)
 * - /api/readiness returns 503 until full initialization completes (too slow for hooks)
 * See: https://github.com/thedotmack/claude-mem/issues/811
 */
async function isWorkerHealthy(): Promise<boolean> {
  const response = await workerHttpRequest('/api/health', { timeoutMs: HEALTH_CHECK_TIMEOUT_MS });
  return response.ok;
}

/**
 * Get the current plugin version from package.json.
 * Returns 'unknown' on ENOENT/EBUSY (shutdown race condition, fix #1042).
 */
function getPluginVersion(): string {
  try {
    const packageJsonPath = path.join(MARKETPLACE_ROOT, 'package.json');
    const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
    return packageJson.version;
  } catch (error: unknown) {
    const code = error instanceof Error ? (error as NodeJS.ErrnoException).code : undefined;
    if (code === 'ENOENT' || code === 'EBUSY') {
      logger.debug('SYSTEM', 'Could not read plugin version (shutdown race)', { code });
      return 'unknown';
    }
    throw error;
  }
}

/**
 * Get the running worker's version from the API
 */
async function getWorkerVersion(): Promise<string> {
  const response = await workerHttpRequest('/api/version', { timeoutMs: HEALTH_CHECK_TIMEOUT_MS });
  if (!response.ok) {
    throw new Error(`Failed to get worker version: ${response.status}`);
  }
  const data = await response.json() as { version: string };
  return data.version;
}

/**
 * Check if worker version matches plugin version
 * Note: Auto-restart on version mismatch is now handled in worker-service.ts start command (issue #484)
 * This function logs for informational purposes only.
 * Skips comparison when either version is 'unknown' (fix #1042 — avoids restart loops).
 */
async function checkWorkerVersion(): Promise<void> {
  let pluginVersion: string;
  try {
    pluginVersion = getPluginVersion();
  } catch (error: unknown) {
    logger.debug('SYSTEM', 'Version check failed reading plugin version', {
      error: error instanceof Error ? error.message : String(error)
    });
    return;
  }

  // Skip version check if plugin version couldn't be read (shutdown race)
  if (pluginVersion === 'unknown') return;

  let workerVersion: string;
  try {
    workerVersion = await getWorkerVersion();
  } catch (error: unknown) {
    logger.debug('SYSTEM', 'Version check failed reading worker version', {
      error: error instanceof Error ? error.message : String(error)
    });
    return;
  }

  // Skip version check if worker version is 'unknown' (avoids restart loops)
  if (workerVersion === 'unknown') return;

  if (pluginVersion !== workerVersion) {
    // Just log debug info - auto-restart handles the mismatch in worker-service.ts
    logger.debug('SYSTEM', 'Version check', {
      pluginVersion,
      workerVersion,
      note: 'Mismatch will be auto-restarted by worker-service start command'
    });
  }
}


/**
 * Ensure worker service is running
 * Quick health check - returns false if worker not healthy (doesn't block)
 * Port might be in use by another process, or worker might not be started yet
 */
export async function ensureWorkerRunning(): Promise<boolean> {
  // Quick health check (single attempt, no polling)
  try {
    if (await isWorkerHealthy()) {
      await checkWorkerVersion();  // logs warning on mismatch, doesn't restart
      return true;  // Worker healthy
    }
  } catch (e) {
    // Not healthy - log for debugging
    logger.debug('SYSTEM', 'Worker health check failed', {
      error: e instanceof Error ? e.message : String(e)
    });
  }

  // Port might be in use by something else, or worker not started
  // Return false but don't throw - let caller decide how to handle
  logger.warn('SYSTEM', 'Worker not healthy, hook will proceed gracefully');

  // When auto-start is disabled, show a toast so the user knows to start manually
  // MUST use loadFromFile() not get() — get() ignores settings.json
  const settings = SettingsDefaultsManager.loadFromFile(USER_SETTINGS_PATH);
  if (settings.CLAUDE_MEM_WORKER_AUTO_START === 'false') {
    showWorkerDownToast();
  }

  return false;
}

// --- Worker-down toast notification (Windows only) ---
const WORKER_TOAST_COOLDOWN_MS = 5 * 60 * 1000; // 5 minutes between toasts

function showWorkerDownToast(): void {
  if (process.platform !== 'win32') return;
  const markerPath = path.join(SettingsDefaultsManager.get('CLAUDE_MEM_DATA_DIR'), '.last-worker-down-toast');
  try {
    // Cooldown: only show one toast per 5 minutes
    if (existsSync(markerPath)) {
      const elapsed = Date.now() - statSync(markerPath).mtimeMs;
      if (elapsed < WORKER_TOAST_COOLDOWN_MS) return;
    }
    writeFileSync(markerPath, '', 'utf-8');
    const ps = Buffer.from(
      `Add-Type -AssemblyName System.Windows.Forms;`
      + `$n=New-Object System.Windows.Forms.NotifyIcon;`
      + `$n.Icon=[System.Drawing.SystemIcons]::Warning;`
      + `$n.BalloonTipTitle='Claude-Mem';`
      + `$n.BalloonTipText='Worker not running — use worker-start.bat to start';`
      + `$n.Visible=$true;`
      + `$n.ShowBalloonTip(5000);`
      + `Start-Sleep 6;$n.Dispose()`,
      'utf16le'
    ).toString('base64');
    exec(`powershell -NoProfile -NonInteractive -EncodedCommand ${ps}`);
  } catch {
    // Toast failure must never block the hook
  }
}
