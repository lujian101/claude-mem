/**
 * GracefulShutdown - Cleanup utilities for graceful exit
 *
 * Extracted from worker-service.ts to provide centralized shutdown coordination.
 * Handles:
 * - HTTP server closure (with Windows-specific delays)
 * - Session manager shutdown coordination
 * - Child process cleanup (Windows zombie port fix)
 */

import http from 'http';
import { logger } from '../../utils/logger.js';
import { stopSupervisor } from '../../supervisor/index.js';

export interface ShutdownableService {
  shutdownAll(): Promise<void>;
}

export interface CloseableClient {
  close(): Promise<void>;
}

export interface CloseableDatabase {
  close(): Promise<void>;
}

/**
 * Stoppable service interface for ChromaMcpManager
 */
export interface StoppableService {
  stop(): Promise<void>;
}

/**
 * Configuration for graceful shutdown
 */
export interface GracefulShutdownConfig {
  server: http.Server | null;
  sessionManager: ShutdownableService;
  mcpClient?: CloseableClient;
  dbManager?: CloseableDatabase;
  chromaMcpManager?: StoppableService;
}

/**
 * Perform graceful shutdown of all services
 *
 * IMPORTANT: On Windows, we must kill all child processes before exiting
 * to prevent zombie ports. The socket handle can be inherited by children,
 * and if not properly closed, the port stays bound after process death.
 */
/**
 * Perform graceful shutdown of all services with detailed timing and error tracking
 *
 * IMPORTANT: On Windows, we must kill all child processes before exiting
 * to prevent zombie ports. The socket handle can be inherited by children,
 * and if not properly closed, the port stays bound after process death.
 */
export async function performGracefulShutdown(config: GracefulShutdownConfig): Promise<void> {
  const shutdownStart = Date.now();
  logger.info('SYSTEM', 'Shutdown initiated', { timestamp: new Date().toISOString() });

  // STEP 1: Close HTTP server first
  const step1Start = Date.now();
  if (config.server) {
    try {
      await closeHttpServer(config.server);
      const step1Elapsed = Date.now() - step1Start;
      logger.info('SYSTEM', 'HTTP server closed', { elapsedMs: step1Elapsed });
    } catch (error) {
      const step1Elapsed = Date.now() - step1Start;
      logger.error('SYSTEM', 'HTTP server close failed', { elapsedMs: step1Elapsed }, error as Error);
    }
  }

  // STEP 2: Shutdown active sessions
  const step2Start = Date.now();
  try {
    await config.sessionManager.shutdownAll();
    const step2Elapsed = Date.now() - step2Start;
    logger.info('SYSTEM', 'Sessions shutdown', { elapsedMs: step2Elapsed });
  } catch (error) {
    const step2Elapsed = Date.now() - step2Start;
    logger.error('SYSTEM', 'Session shutdown failed', { elapsedMs: step2Elapsed }, error as Error);
  }

  // STEP 3: Close MCP client connection (signals child to exit gracefully)
  const step3Start = Date.now();
  if (config.mcpClient) {
    try {
      await config.mcpClient.close();
      const step3Elapsed = Date.now() - step3Start;
      logger.info('SYSTEM', 'MCP client closed', { elapsedMs: step3Elapsed });
    } catch (error) {
      const step3Elapsed = Date.now() - step3Start;
      logger.error('SYSTEM', 'MCP client close failed', { elapsedMs: step3Elapsed }, error as Error);
    }
  }

  // STEP 4: Stop Chroma MCP connection
  const step4Start = Date.now();
  if (config.chromaMcpManager) {
    try {
      logger.info('SHUTDOWN', 'Stopping Chroma MCP connection...');
      await config.chromaMcpManager.stop();
      const step4Elapsed = Date.now() - step4Start;
      logger.info('SHUTDOWN', 'Chroma MCP connection stopped', { elapsedMs: step4Elapsed });
    } catch (error) {
      const step4Elapsed = Date.now() - step4Start;
      logger.error('SHUTDOWN', 'Chroma MCP stop failed', { elapsedMs: step4Elapsed }, error as Error);
    }
  }

  // STEP 5: Close database connection (includes ChromaSync cleanup)
  const step5Start = Date.now();
  if (config.dbManager) {
    try {
      await config.dbManager.close();
      const step5Elapsed = Date.now() - step5Start;
      logger.info('SYSTEM', 'Database closed', { elapsedMs: step5Elapsed });
    } catch (error) {
      const step5Elapsed = Date.now() - step5Start;
      logger.error('SYSTEM', 'Database close failed', { elapsedMs: step5Elapsed }, error as Error);
    }
  }

  // STEP 6: Supervisor handles tracked child termination, PID cleanup, and stale sockets.
  const step6Start = Date.now();
  try {
    await stopSupervisor();
    const step6Elapsed = Date.now() - step6Start;
    logger.info('SYSTEM', 'Supervisor stopped', { elapsedMs: step6Elapsed });
  } catch (error) {
    const step6Elapsed = Date.now() - step6Start;
    logger.error('SYSTEM', 'Supervisor stop failed', { elapsedMs: step6Elapsed }, error as Error);
  }

  const totalElapsed = Date.now() - shutdownStart;
  logger.info('SYSTEM', 'Worker shutdown complete', { totalElapsedMs: totalElapsed });
}

/**
 * Close HTTP server with Windows-specific delays
 * Windows needs extra time to release sockets properly
 */
async function closeHttpServer(server: http.Server): Promise<void> {
  // Close all active connections
  server.closeAllConnections();

  // Give Windows time to close connections before closing server (prevents zombie ports)
  if (process.platform === 'win32') {
    await new Promise(r => setTimeout(r, 500));
  }

  // Close the server
  await new Promise<void>((resolve, reject) => {
    server.close(err => err ? reject(err) : resolve());
  });

  // Extra delay on Windows to ensure port is fully released
  if (process.platform === 'win32') {
    await new Promise(r => setTimeout(r, 500));
    logger.info('SYSTEM', 'Waited for Windows port cleanup');
  }
}
