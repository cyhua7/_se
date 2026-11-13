#!/usr/bin/env node
import { cp, readdir, rename, readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const argv = process.argv.slice(2);
const force = argv.includes('--force') || argv.includes('-f');
const targetArg = argv.find((arg) => !arg.startsWith('-')) || 'bookmark-vault';
const target = path.resolve(process.cwd(), targetArg);

if (existsSync(target)) {
  const entries = await readdir(target).catch(() => []);
  if (entries.length > 0 && !force) {
    console.error(`\n✖ 目標資料夾不是空的：${target}`);
    console.error('  請換一個專案名稱，或加上 --force 覆蓋既有檔案。\n');
    process.exit(1);
  }
}

const templateDir = fileURLToPath(new URL('../template/', import.meta.url));
await cp(templateDir, target, { recursive: true, force: true });

for (const [from, to] of [
  ['gitignore', '.gitignore'],
  ['dev.vars.example', '.dev.vars.example'],
]) {
  const source = path.join(target, from);
  if (existsSync(source)) await rename(source, path.join(target, to));
}

const pkgPath = path.join(target, 'package.json');
const pkg = JSON.parse(await readFile(pkgPath, 'utf8'));
pkg.name = path
  .basename(target)
  .toLowerCase()
  .replace(/[^a-z0-9._-]+/g, '-')
  .replace(/^-+|-+$/g, '') || 'bookmark-vault-app';
await writeFile(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`, 'utf8');

const relative = path.relative(process.cwd(), target) || '.';

console.log(`\n✔ 已建立 Bookmark Vault 專案：${target}\n`);
console.log('接下來：');
console.log(`  cd ${relative}`);
console.log('  npm install');
console.log('  npx wrangler login');
console.log('  npx wrangler d1 create bookmark-db        # 記下 database_id');
console.log('  npx wrangler kv namespace create bookmark-covers  # 記下 id');
console.log('  # 將上面兩個值填進 wrangler.toml');
console.log('  npm run db:remote');
console.log('  npm run deploy');
console.log('\n本機開發：npm run db:local && npm run dev\n');
