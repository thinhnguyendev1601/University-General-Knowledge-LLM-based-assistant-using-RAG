import { readFile } from 'node:fs/promises';
const css = await readFile('src/styles/tokens.css', 'utf8');
const tokens = Object.fromEntries([...css.matchAll(/(--[\w-]+):\s*(#[\da-f]{6})/gi)].map(match => [match[1], match[2]]));
function luminance(hex) {
  const [r, g, b] = hex.slice(1).match(/../g).map(value => parseInt(value, 16) / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return .2126 * r + .7152 * g + .0722 * b;
}
const pairs = [
  ['--text-primary', '--bg-surface', 4.5], ['--text-secondary', '--bg-sidebar', 4.5], ['--text-muted', '--bg-surface', 4.5],
  ['--text-on-primary', '--action-primary', 4.5], ['--text-on-primary', '--action-danger', 4.5], ['--text-link', '--bg-surface', 4.5],
  ['--blue-ink', '--blue-soft', 4.5], ['--green-ink', '--green-soft', 4.5], ['--violet-ink', '--violet-soft', 4.5], ['--amber-ink', '--amber-soft', 4.5], ['--red-ink', '--red-soft', 4.5],
  ['--text-disabled', '--bg-disabled', 4.5], ['--border-control', '--bg-surface', 3], ['--border-control', '--bg-sidebar', 3], ['--focus-ring', '--bg-surface', 3]
];
for (const [foreground, background, minimum] of pairs) {
  const light = luminance(tokens[foreground]); const dark = luminance(tokens[background]);
  const contrast = (Math.max(light, dark) + .05) / (Math.min(light, dark) + .05);
  console.log(`${contrast >= minimum ? 'PASS' : 'FAIL'} ${foreground} / ${background}: ${contrast.toFixed(2)}:1`);
  if (contrast < minimum) process.exitCode = 1;
}
