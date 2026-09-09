import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read from root .env
const envPath = path.resolve(__dirname, '../../.env');
const envVars = {};
if (fs.existsSync(envPath)) {
  const content = fs.readFileSync(envPath, 'utf8');
  content.split('\n').forEach(line => {
    const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
    if (match) {
      const key = match[1];
      const val = match[2] ? match[2].trim() : '';
      if (key.startsWith('NEXT_PUBLIC_')) {
        envVars[key] = val;
      }
    }
  });
}

/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    env: envVars,
};

export default nextConfig;
