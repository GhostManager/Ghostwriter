/**
 * Docker Rebuild Diagnostics Agent
 *
 * A comprehensive utility for automating Docker service rebuild, testing, and diagnostics
 * with detailed error categorization and recovery suggestions.
 *
 * Usage:
 *   const agent = new DockerRebuildAgent();
 *   const result = await agent.rebuild({
 *     service: 'collab-server',
 *     composeFile: 'local.yml',
 *     composeDir: '/home/debian/Ghostwriter'
 *   });
 *
 * See: /home/debian/Ghostwriter/DOCKER_REBUILD_AGENT.md for full documentation
 */

import { exec } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { promisify } from 'util';

const execAsync = promisify(exec);

// ============================================================================
// Type Definitions
// ============================================================================

export interface DockerRebuildRequest {
  service: string;
  composeFile: string;
  composeDir: string;
  maxWaitSeconds?: number;
  logTailLines?: number;
  expectedPatterns?: string[];
  errorPatterns?: string[];
}

export interface DockerRebuildResponse {
  status: 'success' | 'failure' | 'timeout' | 'partial';
  buildOutput: {
    startTime: string;
    endTime: string;
    duration: string;
    buildSucceeded: boolean;
    commandOutput?: string;
  };
  containerStatus: {
    isRunning: boolean;
    uptime?: string;
    port?: string;
    healthStatus?: 'healthy' | 'unhealthy' | 'unknown';
    restartCount?: number;
  };
  logs: {
    recentLines: string[];
    successIndicators: string[];
    errorIndicators: string[];
  };
  diagnosis: {
    summary: string;
    issues: Issue[];
  };
  nextSteps: string[];
  rawMetadata?: {
    containerHash?: string;
    imageId?: string;
    exitCode?: number;
  };
}

export interface Issue {
  severity: 'error' | 'warning' | 'info';
  category: string;
  message: string;
  suggestedFix: string;
  matchedLine?: string;
  relatedKeywords: string[];
}

// ============================================================================
// Error Pattern Definitions
// ============================================================================

const ERROR_PATTERNS = {
  compilation: [
    /SyntaxError/i,
    /TypeError/i,
    /not exported/i,
    /Cannot find module/i,
    /is not defined/i,
    /error TS\d+/i,
    /failed to resolve/i,
  ],
  connectivity: [
    /ECONNREFUSED/i,
    /Connection refused/i,
    /EHOSTUNREACH/i,
    /ENOTFOUND/i,
    /unable to connect/i,
    /network unreachable/i,
  ],
  permission: [
    /EACCES/i,
    /Permission denied/i,
    /EPERM/i,
    /access denied/i,
    /not permitted/i,
  ],
  dependency: [
    /npm ERR!/i,
    /missing module/i,
    /not found/i,
    /peer dep/i,
    /invalid peer/i,
    /unmet peer/i,
  ],
  runtime: [
    /Error:/i,
    /Exception/i,
    /Crash/i,
    /FATAL/i,
    /panic/i,
    /stack trace/i,
  ],
  timeout: [
    /timeout/i,
    /timed out/i,
    /start_period exceeded/i,
    /never became healthy/i,
    /startup timeout/i,
  ],
};

const RECOVERY_SUGGESTIONS = {
  compilation: [
    'Run npm install to ensure all dependencies are installed',
    'Check TypeScript configuration in tsconfig.json',
    'Verify all imports are correct and modules are exported',
    'Clear npm cache: npm cache clean --force',
    'Run npm run build to check for compilation issues locally',
    'Check for circular dependencies in imports',
  ],
  connectivity: [
    'Verify dependent services are running: docker compose ps',
    'Check docker network connectivity with: docker network inspect',
    'Ensure correct hostnames in environment variables',
    'Verify ports are exposed correctly in docker-compose.yml',
    'Check firewall rules for container networking',
    'Verify DNS resolution: docker exec {container} nslookup {host}',
  ],
  permission: [
    'Fix file permissions: chmod -R u+rw,g+r <path>',
    'Check volume mount permissions in docker-compose.yml',
    'Ensure Docker daemon has proper permissions',
    'Verify mount points exist and are accessible',
    'Check ownership of mounted volumes',
  ],
  dependency: [
    'Reinstall dependencies: rm -rf node_modules && npm install',
    'Update package-lock.json: npm ci',
    'Check for peer dependency conflicts',
    'Verify all required packages are in package.json',
    'Clear npm cache: npm cache clean --force',
    'Check Node.js version compatibility',
  ],
  runtime: [
    'Check environment variables are set correctly',
    'Verify configuration files exist and are readable',
    'Review application startup logs for errors',
    'Check system resources: docker stats',
    'Verify all dependencies are available and running',
    'Check for environment variable typos',
  ],
  timeout: [
    'Increase maxWaitSeconds timeout parameter',
    'Check system resources: docker stats',
    'Verify all dependencies are running first',
    'Review startup logs for slow operations',
    'Check network connectivity to dependency services',
    'Consider parallelizing dependency startup',
  ],
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Parse docker ps output to extract container status
 */
function parseDockerPsOutput(output: string): {
  isRunning: boolean;
  status: string;
  ports?: string;
  uptime?: string;
} {
  const lines = output.trim().split('\n');
  if (lines.length < 2) {
    return { isRunning: false, status: 'not found' };
  }

  const statusLine = lines[1];
  const parts = statusLine.split(/\s+/);

  if (parts.length < 6) {
    return { isRunning: false, status: statusLine };
  }

  const status = parts.slice(4).join(' ');
  const isRunning = status.includes('Up') || status.includes('running');
  const ports = statusLine.includes(':') ? statusLine.match(/\d+:\d+/)?.[0] : undefined;

  return {
    isRunning,
    status,
    ports,
  };
}

/**
 * Calculate human-readable duration
 */
function formatDuration(startTime: Date, endTime: Date): string {
  const seconds = Math.round((endTime.getTime() - startTime.getTime()) / 1000);

  if (seconds < 60) {
    return `${seconds} second${seconds !== 1 ? 's' : ''}`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (remainingSeconds === 0) {
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  }

  return `${minutes} minute${minutes !== 1 ? 's' : ''} ${remainingSeconds} second${remainingSeconds !== 1 ? 's' : ''}`;
}

/**
 * Extract port from docker ps output
 */
function extractPort(dockerPsOutput: string): string | undefined {
  const portMatch = dockerPsOutput.match(/0\.0\.0\.0:(\d+)->/);
  if (portMatch) {
    return portMatch[1];
  }

  const portMatch2 = dockerPsOutput.match(/:(\d+)->/);
  if (portMatch2) {
    return portMatch2[1];
  }

  return undefined;
}

/**
 * Parse uptime from docker ps status line
 */
function extractUptime(statusLine: string): string | undefined {
  const uptimeMatch = statusLine.match(/Up (.*?)(\s+ago)?$/);
  if (uptimeMatch) {
    return uptimeMatch[1];
  }
  return undefined;
}

/**
 * Categorize errors by type
 */
function categorizeError(line: string): string | null {
  for (const [category, patterns] of Object.entries(ERROR_PATTERNS)) {
    if (patterns.some(pattern => pattern.test(line))) {
      return category;
    }
  }
  return null;
}

/**
 * Find error issues in logs
 */
function findIssuesInLogs(
  lines: string[],
  customErrorPatterns?: string[]
): Issue[] {
  const issues: Issue[] = [];
  const seenErrors = new Set<string>();

  for (const line of lines) {
    // Check custom patterns first
    if (customErrorPatterns) {
      for (const pattern of customErrorPatterns) {
        try {
          const regex = new RegExp(pattern, 'i');
          if (regex.test(line) && !seenErrors.has(line)) {
            const category = categorizeError(line) || 'runtime';
            issues.push({
              severity: 'error',
              category,
              message: `Error detected: ${line.substring(0, 100)}`,
              suggestedFix: (RECOVERY_SUGGESTIONS[category as keyof typeof RECOVERY_SUGGESTIONS] || [])[0] || 'Review logs for details',
              matchedLine: line,
              relatedKeywords: extractKeywords(line),
            });
            seenErrors.add(line);
            break;
          }
        } catch (e) {
          // Invalid regex, skip
        }
      }
    }

    // Check built-in patterns
    const category = categorizeError(line);
    if (category && !seenErrors.has(line)) {
      issues.push({
        severity: 'error',
        category,
        message: `${category.charAt(0).toUpperCase() + category.slice(1)} error detected`,
        suggestedFix: (RECOVERY_SUGGESTIONS[category as keyof typeof RECOVERY_SUGGESTIONS] || [])[0] || 'Review logs for details',
        matchedLine: line,
        relatedKeywords: extractKeywords(line),
      });
      seenErrors.add(line);
    }
  }

  return issues;
}

/**
 * Extract relevant keywords from error line
 */
function extractKeywords(line: string): string[] {
  const keywords: string[] = [];

  const patterns = [
    /error TS\d+/i,
    /Error: [\w\s]+/i,
    /npm ERR!/i,
    /ECONNREFUSED/i,
    /EACCES/i,
    /ENOTFOUND/i,
  ];

  for (const pattern of patterns) {
    const match = line.match(pattern);
    if (match) {
      keywords.push(match[0]);
    }
  }

  return keywords.length > 0 ? keywords : ['error'];
}

/**
 * Match success patterns in logs
 */
function findSuccessIndicators(
  lines: string[],
  patterns?: string[]
): string[] {
  const matches: string[] = [];

  const defaultPatterns = [
    'listening on port',
    'server running',
    'started successfully',
    'ready',
    'healthy',
    'initialized',
  ];

  const patternsToCheck = patterns || defaultPatterns;

  for (const line of lines) {
    for (const pattern of patternsToCheck) {
      try {
        const regex = new RegExp(pattern, 'i');
        if (regex.test(line) && !matches.includes(line)) {
          matches.push(line);
        }
      } catch (e) {
        // Invalid regex, skip
      }
    }
  }

  return matches;
}

/**
 * Parse docker ps health status
 */
function parseHealthStatus(
  dockerPsOutput: string
): 'healthy' | 'unhealthy' | 'unknown' {
  if (dockerPsOutput.includes('(healthy)')) {
    return 'healthy';
  }
  if (dockerPsOutput.includes('(unhealthy)')) {
    return 'unhealthy';
  }
  return 'unknown';
}

/**
 * Parse restart count from docker inspect
 */
async function getRestartCount(
  composeDir: string,
  composeFile: string,
  service: string
): Promise<number | undefined> {
  try {
    const { stdout } = await execAsync(
      `cd ${composeDir} && docker compose -f ${composeFile} ps ${service} --format json`,
    );

    const containers = JSON.parse(stdout);
    if (Array.isArray(containers) && containers.length > 0) {
      return (containers[0] as any).RestartCount || 0;
    }
  } catch (e) {
    // Couldn't parse, return undefined
  }
  return undefined;
}

// ============================================================================
// Docker Rebuild Agent Class
// ============================================================================

export class DockerRebuildAgent {
  /**
   * Execute the full rebuild and diagnostics cycle
   */
  async rebuild(request: DockerRebuildRequest): Promise<DockerRebuildResponse> {
    const {
      service,
      composeFile,
      composeDir,
      maxWaitSeconds = 30,
      logTailLines = 50,
      expectedPatterns,
      errorPatterns,
    } = request;

    const startTime = new Date();
    let buildSucceeded = false;
    let containerIsRunning = false;
    let containerPort: string | undefined;
    let healthStatus: 'healthy' | 'unhealthy' | 'unknown' = 'unknown';
    let restartCount: number | undefined;
    let logs: string[] = [];
    let successIndicators: string[] = [];
    let errorIndicators: string[] = [];
    let issues: Issue[] = [];
    let status: 'success' | 'failure' | 'timeout' | 'partial' = 'failure';

    try {
      // ======================================================================
      // Phase 1: Verify
      // ======================================================================
      await this.phase1Verify(composeDir, composeFile, service);

      // ======================================================================
      // Phase 2: Stop (Graceful)
      // ======================================================================
      await this.phase2Stop(composeDir, composeFile, service);

      // ======================================================================
      // Phase 3: Rebuild
      // ======================================================================
      buildSucceeded = await this.phase3Rebuild(composeDir, composeFile, service);

      // ======================================================================
      // Phase 4: Wait & Poll
      // ======================================================================
      const waitResult = await this.phase4Wait(
        composeDir,
        composeFile,
        service,
        maxWaitSeconds,
      );
      containerIsRunning = waitResult.isRunning;

      // ======================================================================
      // Phase 5: Analyze Logs
      // ======================================================================
      const logResult = await this.phase5AnalyzeLogs(
        composeDir,
        composeFile,
        service,
        logTailLines,
      );
      logs = logResult.lines;

      // ======================================================================
      // Phase 6: Diagnose & Categorize
      // ======================================================================
      const diagnosisResult = await this.phase6Diagnose(
        composeDir,
        composeFile,
        service,
        logs,
        expectedPatterns,
        errorPatterns,
      );

      successIndicators = diagnosisResult.successIndicators;
      errorIndicators = diagnosisResult.errorIndicators;
      issues = diagnosisResult.issues;
      containerPort = diagnosisResult.port;
      healthStatus = diagnosisResult.healthStatus;
      restartCount = diagnosisResult.restartCount;

      // ======================================================================
      // Phase 7: Determine Final Status
      // ======================================================================
      if (buildSucceeded && containerIsRunning && successIndicators.length > 0) {
        status = 'success';
      } else if (!buildSucceeded) {
        status = 'failure';
      } else if (!containerIsRunning) {
        status = 'failure';
      } else if (successIndicators.length === 0) {
        status = 'timeout';
      }
    } catch (error: any) {
      issues.push({
        severity: 'error',
        category: 'runtime',
        message: `Agent execution error: ${error.message}`,
        suggestedFix: 'Check logs and ensure all parameters are correct',
        relatedKeywords: ['execution', 'error'],
      });
      status = 'failure';
    }

    const endTime = new Date();

    return {
      status,
      buildOutput: {
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        duration: formatDuration(startTime, endTime),
        buildSucceeded,
      },
      containerStatus: {
        isRunning: containerIsRunning,
        port: containerPort,
        healthStatus,
        restartCount,
      },
      logs: {
        recentLines: logs,
        successIndicators,
        errorIndicators,
      },
      diagnosis: {
        summary: this.generateSummary(status, issues, buildSucceeded, containerIsRunning),
        issues,
      },
      nextSteps: this.generateNextSteps(status, issues, buildSucceeded, containerIsRunning),
    };
  }

  /**
   * Phase 1: Verify compose file and service exist
   */
  private async phase1Verify(
    composeDir: string,
    composeFile: string,
    service: string,
  ): Promise<void> {
    const composePath = path.join(composeDir, composeFile);

    if (!fs.existsSync(composePath)) {
      throw new Error(`Compose file not found: ${composePath}`);
    }

    const content = fs.readFileSync(composePath, 'utf-8');
    if (!content.includes(`${service}:`)) {
      throw new Error(`Service '${service}' not found in ${composePath}`);
    }
  }

  /**
   * Phase 2: Stop the service gracefully
   */
  private async phase2Stop(
    composeDir: string,
    composeFile: string,
    service: string,
  ): Promise<void> {
    try {
      await execAsync(
        `cd ${composeDir} && docker compose -f ${composeFile} down ${service}`,
        { timeout: 15000 },
      );
    } catch (e) {
      // Service might not be running, that's okay
    }

    // Wait a bit for graceful shutdown
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  /**
   * Phase 3: Rebuild the service
   */
  private async phase3Rebuild(
    composeDir: string,
    composeFile: string,
    service: string,
  ): Promise<boolean> {
    try {
      await execAsync(
        `cd ${composeDir} && docker compose -f ${composeFile} up --build -d ${service}`,
        { timeout: 120000, maxBuffer: 10 * 1024 * 1024 },
      );
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Phase 4: Wait for service to be ready
   */
  private async phase4Wait(
    composeDir: string,
    composeFile: string,
    service: string,
    maxWaitSeconds: number,
  ): Promise<{ isRunning: boolean }> {
    const pollInterval = 2000;
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitSeconds * 1000) {
      try {
        const { stdout } = await execAsync(
          `cd ${composeDir} && docker compose -f ${composeFile} ps ${service}`,
        );

        const psResult = parseDockerPsOutput(stdout);
        if (psResult.isRunning) {
          return { isRunning: true };
        }
      } catch (e) {
        // Service check failed, try again
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    return { isRunning: false };
  }

  /**
   * Phase 5: Analyze container logs
   */
  private async phase5AnalyzeLogs(
    composeDir: string,
    composeFile: string,
    service: string,
    logTailLines: number,
  ): Promise<{ lines: string[] }> {
    try {
      const { stdout } = await execAsync(
        `cd ${composeDir} && docker compose -f ${composeFile} logs --tail=${logTailLines} ${service}`,
      );

      const lines = stdout
        .split('\n')
        .filter(line => line.trim().length > 0)
        .slice(0, logTailLines);

      return { lines };
    } catch (e) {
      return { lines: [] };
    }
  }

  /**
   * Phase 6: Diagnose issues and categorize
   */
  private async phase6Diagnose(
    composeDir: string,
    composeFile: string,
    service: string,
    logs: string[],
    expectedPatterns?: string[],
    errorPatterns?: string[],
  ): Promise<{
    successIndicators: string[];
    errorIndicators: string[];
    issues: Issue[];
    port?: string;
    healthStatus: 'healthy' | 'unhealthy' | 'unknown';
    restartCount?: number;
  }> {
    // Check success indicators
    const successIndicators = findSuccessIndicators(logs, expectedPatterns);

    // Check error indicators
    let errorIndicators: string[] = [];
    if (errorPatterns) {
      for (const line of logs) {
        for (const pattern of errorPatterns) {
          try {
            const regex = new RegExp(pattern, 'i');
            if (regex.test(line) && !errorIndicators.includes(line)) {
              errorIndicators.push(line);
            }
          } catch (e) {
            // Invalid regex, skip
          }
        }
      }
    }

    // Find issues
    const issues = findIssuesInLogs(logs, errorPatterns);

    // Get port
    let port: string | undefined;
    try {
      const { stdout } = await execAsync(
        `cd ${composeDir} && docker compose -f ${composeFile} ps ${service}`,
      );
      port = extractPort(stdout);
    } catch (e) {
      // Couldn't get port
    }

    // Get health status
    let healthStatus: 'healthy' | 'unhealthy' | 'unknown' = 'unknown';
    try {
      const { stdout } = await execAsync(
        `cd ${composeDir} && docker compose -f ${composeFile} ps ${service}`,
      );
      healthStatus = parseHealthStatus(stdout);
    } catch (e) {
      // Couldn't determine health status
    }

    // Get restart count
    const restartCount = await getRestartCount(composeDir, composeFile, service);

    return {
      successIndicators,
      errorIndicators,
      issues,
      port,
      healthStatus,
      restartCount,
    };
  }

  /**
   * Generate summary sentence
   */
  private generateSummary(
    status: string,
    issues: Issue[],
    buildSucceeded: boolean,
    containerIsRunning: boolean,
  ): string {
    if (status === 'success') {
      return 'Service rebuilt successfully and is running healthy.';
    }

    if (!buildSucceeded) {
      const errorCount = issues.length;
      return `Build failed with ${errorCount} error${errorCount !== 1 ? 's' : ''}.`;
    }

    if (!containerIsRunning) {
      return 'Service built but container is not running.';
    }

    return 'Service started but did not become healthy within timeout.';
  }

  /**
   * Generate next steps
   */
  private generateNextSteps(
    status: string,
    issues: Issue[],
    buildSucceeded: boolean,
    containerIsRunning: boolean,
  ): string[] {
    const steps: string[] = [];

    if (status === 'success') {
      steps.push('Service is ready for testing');
      return steps;
    }

    if (!buildSucceeded) {
      issues.forEach(issue => {
        steps.push(issue.suggestedFix.split('\n')[0]); // First suggestion
      });
      return steps;
    }

    if (!containerIsRunning) {
      steps.push('Check service logs: docker compose logs {service}');
      steps.push('Verify dependencies are running: docker compose ps');
      steps.push('Review error patterns in logs');
      return steps;
    }

    steps.push('Increase timeout and retry with: --maxWaitSeconds 60');
    steps.push('Check system resources: docker stats');
    steps.push('Review dependency services: docker compose logs');

    return steps;
  }
}

// ============================================================================
// Export for CLI Usage
// ============================================================================

export async function executeRebuild(
  request: DockerRebuildRequest,
): Promise<string> {
  const agent = new DockerRebuildAgent();
  const result = await agent.rebuild(request);
  return JSON.stringify(result, null, 2);
}
