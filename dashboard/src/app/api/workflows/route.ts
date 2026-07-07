import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';

const workflowsDir = path.resolve(process.cwd(), '../src/workflows');

function convertUiToApi(uiJson: any, objectInfo: any): any {
  if (!uiJson || !uiJson.nodes) return uiJson;

  const linkMap: Record<string, [string, number]> = {};
  if (Array.isArray(uiJson.links)) {
    for (const link of uiJson.links) {
      if (!link) continue;
      const [linkId, originNode, originSlot, targetNode, targetSlot] = link;
      linkMap[String(linkId)] = [String(originNode), Number(originSlot)];
    }
  }

  const apiJson: Record<string, any> = {};
  for (const node of uiJson.nodes) {
    if (!node) continue;
    const nodeId = String(node.id);
    const classType = node.type;

    const inputs: Record<string, any> = {};
    const nodeInfo = objectInfo?.[classType];
    
    if (nodeInfo) {
      const requiredInputs = nodeInfo.input?.required || {};
      const optionalInputs = nodeInfo.input?.optional || {};
      const inputSpecs = [...Object.entries(requiredInputs), ...Object.entries(optionalInputs)];

      const widgetSpecs: string[] = [];
      for (const [name, spec] of inputSpecs) {
        let isWidget = false;
        if (Array.isArray(spec)) {
          if (Array.isArray(spec[0])) {
            isWidget = true;
          } else if (typeof spec[0] === 'string' && ['int', 'float', 'string', 'boolean', 'combo', 'number'].includes(spec[0].toLowerCase())) {
            isWidget = true;
          } else if (typeof spec[0] === 'string' && spec[0] !== spec[0].toUpperCase()) {
            isWidget = true;
          }
        }
        if (isWidget) {
          widgetSpecs.push(name);
        }
      }

      const widgetsValues = node.widgets_values || [];
      for (let i = 0; i < widgetsValues.length; i++) {
        if (i < widgetSpecs.length) {
          inputs[widgetSpecs[i]] = widgetsValues[i];
        }
      }
    }

    if (Array.isArray(node.inputs)) {
      for (const slot of node.inputs) {
        const slotName = slot.name;
        const linkId = slot.link;
        if (linkId !== null && linkId !== undefined && linkMap[String(linkId)]) {
          inputs[slotName] = linkMap[String(linkId)];
        }
      }
    }

    apiJson[nodeId] = {
      inputs,
      class_type: classType,
      _meta: {
        title: node.title || node.properties?.NodeNameForTitle || classType
      }
    };
  }

  return apiJson;
}

export async function GET() {
  try {
    if (!fs.existsSync(workflowsDir)) {
      return NextResponse.json({ workflows: [] });
    }
    const files = fs.readdirSync(workflowsDir)
      .filter(f => f.endsWith('.json'))
      .map(f => ({
        name: f,
        path: path.join(workflowsDir, f)
      }));
    
    return NextResponse.json({ workflows: files });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to list workflows' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    let { action, filename, manifest, jsonPath, workflow } = body;
    
    if (action === 'load') {
      if (!fs.existsSync(jsonPath)) throw new Error('File not found');
      let workflowData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
      
      // Try to find matching manifest
      const yamlPath = jsonPath.replace('.json', '.yaml');
      let manifestData = null;
      if (fs.existsSync(yamlPath)) {
        manifestData = yaml.load(fs.readFileSync(yamlPath, 'utf8'));
      }

      // Fetch Object Info from ComfyUI
      let objectInfo = null;
      try {
        const envPath = path.resolve(process.cwd(), '../.env');
        let comfyUrl = 'http://127.0.0.1:8188';
        if (fs.existsSync(envPath)) {
          const envContent = fs.readFileSync(envPath, 'utf8');
          const lines = envContent.split('\n');
          for (const line of lines) {
            if (line.startsWith('COMFY_URL=')) {
              comfyUrl = line.split('=')[1]?.trim() || comfyUrl;
              break;
            }
          }
        }
          
        const res = await fetch(`${comfyUrl}/object_info`);
        objectInfo = await res.json();
      } catch (e) {
        console.warn('Failed to fetch object_info from ComfyUI:', e);
      }
      
      // If the loaded workflow is in UI (Full) format, convert it to API format on the fly
      if (workflowData && 'nodes' in workflowData && 'links' in workflowData) {
        workflowData = convertUiToApi(workflowData, objectInfo);
      }
      
      return NextResponse.json({ workflow: workflowData, manifest: manifestData, objectInfo });
    }
    
    if (action === 'save') {
      // Strip .json extension first so we get "FluxDev" as the base, then produce "FluxDev.yaml" and "FluxDev.json"
      const baseName = filename.replace(/\.json$/i, '').replace(/\.yaml$/i, '');
      const yamlPath = path.join(workflowsDir, `${baseName}.yaml`);
      const jsonPath = path.join(workflowsDir, `${baseName}.json`);
      
      // Save YAML Manifest
      const yamlContent = yaml.dump(manifest, { indent: 2 });
      fs.writeFileSync(yamlPath, yamlContent, 'utf8');
      
      // Save JSON Workflow (if provided)
      if (workflow) {
        fs.writeFileSync(jsonPath, JSON.stringify(workflow, null, 2), 'utf8');
      }
      
      return NextResponse.json({ status: 'success', yamlPath, jsonPath });
    }
    
    if (action === 'import') {
      const { filename, workflow } = body;
      
      if (typeof workflow !== 'object' || workflow === null || Array.isArray(workflow)) {
        throw new Error('Invalid JSON structure. Must be a ComfyUI workflow.');
      }
      
      const keys = Object.keys(workflow);
      if (keys.length === 0) throw new Error('Empty workflow JSON.');
      
      const isFullWorkflow = 'nodes' in workflow && 'links' in workflow;
      if (!isFullWorkflow) {
        // Validate node structure for API Format workflows
        for (const key of keys.slice(0, 3)) {
          const node = workflow[key];
          if (typeof node !== 'object' || !node.class_type || !node.inputs) {
             throw new Error('Invalid node structure. Please ensure this is an API Format workflow.');
          }
        }
      }
      
      const cleanName = filename.endsWith('.json') ? filename : `${filename}.json`;
      const importPath = path.join(workflowsDir, cleanName);
      
      fs.writeFileSync(importPath, JSON.stringify(workflow, null, 2), 'utf8');
      return NextResponse.json({ status: 'success', filename: cleanName });
    }
    
    if (action === 'delete') {
      const { filename } = body;
      if (!filename) throw new Error('Filename required');
      
      const baseName = filename.replace(/\.json$/i, '').replace(/\.yaml$/i, '');
      const jsonPath = path.join(workflowsDir, `${baseName}.json`);
      const yamlPath = path.join(workflowsDir, `${baseName}.yaml`);
      
      if (fs.existsSync(jsonPath)) fs.unlinkSync(jsonPath);
      if (fs.existsSync(yamlPath)) fs.unlinkSync(yamlPath);
      
      return NextResponse.json({ status: 'success' });
    }
    
    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
