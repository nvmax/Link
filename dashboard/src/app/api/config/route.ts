import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const envPath = path.resolve(process.cwd(), '../.env');

export async function GET() {
  try {
    if (!fs.existsSync(envPath)) {
      return NextResponse.json({ config: {} });
    }
    const content = fs.readFileSync(envPath, 'utf8');
    const config: Record<string, string> = {};
    
    content.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...value] = trimmed.split('=');
        if (key) config[key.trim()] = value.join('=').trim();
      }
    });
    
    return NextResponse.json({ config });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to read config' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    // Support both { config: { ... } } and { ... }
    const config = body.config || body;
    
    let content = '';
    if (fs.existsSync(envPath)) {
      content = fs.readFileSync(envPath, 'utf8');
    }
    
    const lines = content.split('\n');
    const updatedLines = [];
    const keysHandled = new Set();
    
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        const key = trimmed.split('=')[0].trim();
        if (config[key] !== undefined && typeof config[key] !== 'object') {
          updatedLines.push(`${key}=${config[key]}`);
          keysHandled.add(key);
        } else {
          updatedLines.push(line);
        }
      } else {
        updatedLines.push(line);
      }
    }
    
    // add any new keys
    for (const [key, value] of Object.entries(config)) {
      if (!keysHandled.has(key) && key !== 'config' && typeof value !== 'object') {
        updatedLines.push(`${key}=${value}`);
      }
    }
    
    fs.writeFileSync(envPath, updatedLines.join('\n'), 'utf8');
    return NextResponse.json({ status: 'success' });
  } catch (error) {
    console.error('Config save error:', error);
    return NextResponse.json({ error: 'Failed to save config' }, { status: 500 });
  }
}
