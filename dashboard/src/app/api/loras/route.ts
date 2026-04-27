import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const lorasDir = path.resolve(process.cwd(), '../src/workflows/loras');

export async function GET() {
  try {
    if (!fs.existsSync(lorasDir)) {
      return NextResponse.json({ loras: [] });
    }
    const files = fs.readdirSync(lorasDir)
      .filter(f => f.endsWith('.json'))
      .map(f => ({
        name: f,
        path: f
      }));
    
    return NextResponse.json({ loras: files });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to list lora files' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const { action, filename, data } = await request.json();
    const filePath = path.join(lorasDir, filename.endsWith('.json') ? filename : `${filename}.json`);

    if (action === 'save') {
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
      return NextResponse.json({ status: 'success' });
    }

    if (action === 'create') {
      if (fs.existsSync(filePath)) {
        return NextResponse.json({ error: 'File already exists' }, { status: 400 });
      }
      const initialData = {
        categories: ["General"],
        available_loras: []
      };
      fs.writeFileSync(filePath, JSON.stringify(initialData, null, 2), 'utf8');
      return NextResponse.json({ status: 'success' });
    }

    if (action === 'load') {
      if (!fs.existsSync(filePath)) throw new Error('File not found');
      const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      return NextResponse.json({ data: content });
    }

    if (action === 'delete_file') {
      if (!fs.existsSync(filePath)) throw new Error('File not found');
      fs.unlinkSync(filePath);
      return NextResponse.json({ status: 'success' });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
