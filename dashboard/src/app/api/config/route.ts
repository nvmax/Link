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
    const { config } = await request.json();
    let content = '';
    
    // We try to preserve comments if we want, but for now let's just write the keys
    // For a cleaner approach, we just rebuild the file
    Object.entries(config).forEach(([key, value]) => {
      content += `${key}=${value}\n`;
    });
    
    fs.writeFileSync(envPath, content, 'utf8');
    return NextResponse.json({ status: 'success' });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to save config' }, { status: 500 });
  }
}
