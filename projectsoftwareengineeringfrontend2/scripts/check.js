import { readdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
async function scan(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = `${directory}/${entry.name}`;
    if (entry.isDirectory()) await scan(file);
    else if (file.endsWith('.js')) {
      const result = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
      if (result.status !== 0) { console.error(result.stderr); process.exitCode = 1; }
    }
  }
}
await scan('src'); await scan('scripts');
await scan('dev'); await scan('tests');
if (!process.exitCode) console.log('JavaScript syntax: OK');
