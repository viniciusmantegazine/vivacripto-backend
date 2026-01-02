import esbuild from 'esbuild';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const result = await esbuild.build({
  entryPoints: ['src/index.ts'],
  bundle: true,
  platform: 'node',
  target: 'node20',
  outfile: 'dist/index.js',
  external: [
    'express',
    'cors',
    'dotenv',
    'drizzle-orm',
    'google-auth-library',
    'jsonwebtoken',
    'mysql2',
    'uuid',
    'tsconfig-paths'
  ],
  sourcemap: true,
  minify: false,
});

console.log('Build completed successfully!');
