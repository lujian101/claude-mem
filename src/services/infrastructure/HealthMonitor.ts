/**
 * HealthMonitor - Port monitoring, health checks, and version checking
 *
 * Extracted from worker-service.ts monolith to provide centralized health monitoring.
 * Handles:
 * - Port availability checking
 * - Worker health/readiness polling
 * - Version mismatch detection (critical for plugin updates)
 * - HTTP-based shutdown requests
 */

import path from 'path';
import net from 'net';
import { readFileSync } from 'fs';
import { logger } from '../../utils/logger.js';
import { MARKETPLACE_ROOT } from '../../shared/paths.js';

/**
 * Check if a port is in use using TCP connection (fast, 1s timeout).
 * This avoids Bun's libuv assertion issues with AbortSignal.timeout on Windows.
 * Returns true if something is listening on the port (doesn't verify it's claude-mem).
 */
async function isPortInUseTcp(port: number, timeoutMs: number = 1000): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let resolved = false;

    const cleanup = () => {
      if (resolved) return;
      resolved = true;
      try {
        socket.destroy();
      } catch {
        // Ignore cleanup errors
      }
    };

    const timeout = setTimeout(() => {
      cleanup();
      resolve(false); // Timeout = port not reachable
    }, timeoutMs);

    socket.connect(port, '127.0.0.1', () => {
      clearTimeout(timeout);
      cleanup();
      resolve(true); // Connected = port in use
    });

    socket.on('error', () => {
      clearTimeout(timeout);
      cleanup();
      resolve(false); // Connection error = port not in use
    });
  });
}

/**
 * Make an HTTP request to the worker via TCP.
 * Returns { ok, statusCode, body } or throws on transport error.
 */
async function httpRequestToWorker(
  port: number,
  endpointPath: string,
  method: string = 'GET'
): Promise<{ ok: boolean; statusCode: number; body: string }> {
  const response = await fetch(`http://127.0.0.1:${port}${endpointPath}`, { method });
  // Gracefully handle cases where response body isn't available (e.g., test mocks)
  let body = '';
  try {
    body = await response.text();
  } catch {
    // Body unavailable — health/readiness checks only need .ok
  }
  return { ok: response.ok, statusCode: response.status, body };
}

/**
 * Check if a port is in use using fast TCP connection.
 * This replaces the previous HTTP-based check which could hang for minutes
 * when the port was occupied by a non-HTTP service or had connection issues.
 *
 * Returns true if something is listening on the port (regardless of whether it's claude-mem).
 * The health check logic in ensureWorkerStarted will verify if it's actually our worker.
 */
export async function isPortInUse(port: number): Promise<boolean> {
  try {
    // Use TCP connection check (1s timeout) instead of HTTP fetch
    // This avoids Bun libuv assertion issues and is much faster
    return await isPortInUseTcp(port, 1000);
  } catch (error) {
    // Treat any error as port not in use (fail open)
    logger.debug('SYSTEM', 'Port check failed, assuming port is free', { port }, error as Error);
    return false;
  }
}

/**
 * Poll a worker endpoint until it returns 200 OK or timeout.
 * Shared implementation for liveness and readiness checks.
 */
async function pollEndpointUntilOk(
  port: number,
  endpointPath: string,
  timeoutMs: number,
  retryLogMessage: string
): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const result = await httpRequestToWorker(port, endpointPath);
      if (result.ok) return true;
    } catch (error) {
      // [ANTI-PATTERN IGNORED]: Retry loop - expected failures during startup, will retry
      logger.debug('SYSTEM', retryLogMessage, {}, error as Error);
    }
    await new Promise(r => setTimeout(r, 500));
  }
  return false;
}

/**
 * Wait for the worker HTTP server to become responsive (liveness check).
 * Uses /api/health which returns 200 as soon as the HTTP server is listening.
 * For full initialization (DB + search), use waitForReadiness() instead.
 */
export function waitForHealth(port: number, timeoutMs: number = 30000): Promise<boolean> {
  return pollEndpointUntilOk(port, '/api/health', timeoutMs, 'Service not ready yet, will retry');
}

/**
 * Wait for the worker to be fully initialized (DB + search ready).
 * Uses /api/readiness which returns 200 only after core initialization completes.
 * Now that initializationCompleteFlag is set after DB/search init (not MCP),
 * this typically completes in a few seconds.
 */
export function waitForReadiness(port: number, timeoutMs: number = 30000): Promise<boolean> {
  return pollEndpointUntilOk(port, '/api/readiness', timeoutMs, 'Worker not ready yet, will retry');
}

/**
 * Wait for a port to become free (no longer responding to health checks)
 * Used after shutdown to confirm the port is available for restart
 */
export async function waitForPortFree(port: number, timeoutMs: number = 10000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (!(await isPortInUse(port))) return true;
    await new Promise(r => setTimeout(r, 500));
  }
  return false;
}

/**
 * Send HTTP shutdown request to a running worker
 * @returns true if shutdown request was acknowledged, false otherwise
 */
export async function httpShutdown(port: number): Promise<boolean> {
  try {
    const result = await httpRequestToWorker(port, '/api/admin/shutdown', 'POST');
    if (!result.ok) {
      logger.warn('SYSTEM', 'Shutdown request returned error', { status: result.statusCode });
      return false;
    }
    return true;
  } catch (error) {
    // Connection refused is expected if worker already stopped
    if (error instanceof Error && error.message?.includes('ECONNREFUSED')) {
      logger.debug('SYSTEM', 'Worker already stopped', {}, error);
      return false;
    }
    // Unexpected error - log full details
    logger.error('SYSTEM', 'Shutdown request failed unexpectedly', {}, error as Error);
    return false;
  }
}

/**
 * Get the plugin version from the installed marketplace package.json
 * This is the "expected" version that should be running.
 * Returns 'unknown' on ENOENT/EBUSY (shutdown race condition, fix #1042).
 */
export function getInstalledPluginVersion(): string {
  try {
    const packageJsonPath = path.join(MARKETPLACE_ROOT, 'package.json');
    const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
    return packageJson.version;
  } catch (error: unknown) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === 'ENOENT' || code === 'EBUSY') {
      logger.debug('SYSTEM', 'Could not read plugin version (shutdown race)', { code });
      return 'unknown';
    }
    throw error;
  }
}

/**
 * Get the running worker's version via API
 * This is the "actual" version currently running.
 */
export async function getRunningWorkerVersion(port: number): Promise<string | null> {
  try {
    const result = await httpRequestToWorker(port, '/api/version');
    if (!result.ok) return null;
    const data = JSON.parse(result.body) as { version: string };
    return data.version;
  } catch {
    // Expected: worker not running or version endpoint unavailable
    logger.debug('SYSTEM', 'Could not fetch worker version', {});
    return null;
  }
}

export interface VersionCheckResult {
  matches: boolean;
  pluginVersion: string;
  workerVersion: string | null;
}

/**
 * Check if worker version matches plugin version
 * Critical for detecting when plugin is updated but worker is still running old code
 * Returns true if versions match or if we can't determine (assume match for graceful degradation)
 */
export async function checkVersionMatch(port: number): Promise<VersionCheckResult> {
  const pluginVersion = getInstalledPluginVersion();
  const workerVersion = await getRunningWorkerVersion(port);

  // If either version is unknown/null, assume match (graceful degradation, fix #1042)
  if (!workerVersion || pluginVersion === 'unknown') {
    return { matches: true, pluginVersion, workerVersion };
  }

  return { matches: pluginVersion === workerVersion, pluginVersion, workerVersion };
}
