import { spawnSync } from 'node:child_process';
import { rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const nextBin = require.resolve('next/dist/bin/next');
const nextDir = fileURLToPath(new URL('../.next', import.meta.url));

rmSync(nextDir, { recursive: true, force: true });

const result = spawnSync(process.execPath, [nextBin, 'build'], {
  stdio: 'inherit',
  env: {
    ...process.env,
    // Next 14 can skip middleware-manifest.json with the build worker on Windows.
    NEXT_PRIVATE_BUILD_WORKER: process.env.NEXT_PRIVATE_BUILD_WORKER ?? '0',
  },
});

process.exit(result.status ?? 1);
