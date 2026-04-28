"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';

interface DashboardContextType {
  activeTab: 'setup' | 'architect' | 'modal-studio' | 'lora-studio';
  setActiveTab: (tab: 'setup' | 'architect' | 'modal-studio' | 'lora-studio') => void;
  viewMode: 'list' | 'visual';
  setViewMode: (mode: 'list' | 'visual') => void;
  config: any;
  setConfig: (config: any) => void;
  saveConfig: (newConfig: any) => Promise<void>;
  workflows: any[];
  selectedWorkflow: any;
  setSelectedWorkflow: (wf: any) => void;
  selections: any[];
  setSelections: (selections: any[]) => void;
  customCommandName: string;
  setCustomCommandName: (name: string) => void;
  uiConfig: any;
  setUiConfig: (config: any) => void;
  loraFiles: any[];
  setLoraFiles: (files: any[]) => void;
  editingLoraFile: any;
  setEditingLoraFile: (file: any) => void;
  loraPage: number;
  setLoraPage: (page: number | ((p: number) => number)) => void;
  loadWorkflow: (wf: any) => Promise<void>;
  saveWorkflow: () => Promise<void>;
  toggleInput: (nodeId: string, field: string, type: string | null) => void;
  updateSelection: (idx: number, updates: any) => void;
  moveInput: (idx: number, dir: 'up' | 'down') => void;
  deleteWorkflow: (wf: any) => Promise<void>;
  importWorkflow: (json: any, name: string) => Promise<void>;
  loadLoraFile: (file: any) => Promise<void>;
  saveLoraFile: () => Promise<void>;
  updateLoraField: (idx: number, field: string, value: any) => void;
  moveLora: (idx: number, dir: 'up' | 'down') => void;
  deleteLora: (idx: number) => void;
  addLora: (initialData?: any) => void;
  createNewLoraList: () => Promise<void>;
  deleteLoraList: (file: any) => Promise<void>;
  loraSelections: Record<string, any>;
  setLoraSelections: (selections: Record<string, any>) => void;
  updateLoraSelection: (nodeId: string, updates: any) => void;
  objectInfo: any;
  updateWorkflowInput: (nodeId: string, field: string, value: any) => void;
  nodeCoords: Record<string, { x: number, y: number }>;
  setNodeCoords: (coords: Record<string, { x: number, y: number }> | ((prev: any) => any)) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

// ---------------------------------------------------------------------------
// Universal type inference — the SINGLE source of truth for Discord input types.
// Used by both the Architect (when toggling inputs) and loadWorkflow
// (to normalize types in existing manifests so re-importing always works).
// ---------------------------------------------------------------------------
function inferDiscordType(
  classType: string,
  field: string,
  objectInfo: any,
  existingType?: string
): { type: string; choices?: any[] } {
  const classLower = (classType || '').toLowerCase();
  const fieldLower = (field || '').toLowerCase();

  // 1. Node class_type keywords (LoadAudio, LoadImage, etc.) — highest priority
  if (classLower.includes('loadaudio') || (classLower.includes('audio') && fieldLower === 'audio')) {
    return { type: 'audio_upload' };
  }
  if (classLower.includes('loadvideo') || classLower.includes('vhs_loadaudio')) {
    return { type: 'video_upload' };
  }
  if (classLower.includes('loadimage') || classLower.includes('imageinput') || classLower.includes('imageloader')) {
    return { type: 'image_upload' };
  }

  // 2. Field name keywords — fallback for uploads
  if (fieldLower.includes('audio') || fieldLower.includes('sound') || fieldLower.includes('music')) {
    return { type: 'audio_upload' };
  }
  if (fieldLower.includes('video') || fieldLower.includes('clip') || fieldLower.includes('footage')) {
    return { type: 'video_upload' };
  }
  if (fieldLower === 'image' || fieldLower === 'img' || fieldLower.includes('image')) {
    return { type: 'image_upload' };
  }

  // 3. ComfyUI objectInfo — enum/choices array → select
  const nodeInfo = objectInfo?.[classType];
  const inputInfo = nodeInfo?.input?.required?.[field] || nodeInfo?.input?.optional?.[field];
  if (Array.isArray(inputInfo) && Array.isArray(inputInfo[0])) {
    return { type: 'select', choices: inputInfo[0] };
  }

  // 4. If existing type is already a valid upload type, keep it
  if (existingType && ['image_upload', 'audio_upload', 'video_upload', 'select'].includes(existingType)) {
    return { type: existingType };
  }

  // 5. Default — free text
  return { type: 'text' };
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState<'setup' | 'architect' | 'modal-studio' | 'lora-studio'>('setup');
  const [viewMode, setViewMode] = useState<'list' | 'visual'>('list');
  const [config, setConfig] = useState<any>({});
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null);
  const [objectInfo, setObjectInfo] = useState<any>(null);
  const [selections, setSelections] = useState<any[]>([]);
  const [customCommandName, setCustomCommandName] = useState<string>('');
  const [uiConfig, setUiConfig] = useState<any>({
    embed: {
      title_template: "{user}'s Generation",
      color: "#5865F2",
      show_metadata: ["prompt", "seed", "model", "ratio"]
    },
    buttons: [
      { type: "regenerate", label: "Regenerate", style: "primary" },
      { type: "options", label: "Options", style: "secondary" },
      { type: "delete", label: "Delete", style: "danger" }
    ]
  });

  const [loraSelections, setLoraSelections] = useState<Record<string, any>>({});
  const [nodeCoords, setNodeCoords] = useState<Record<string, { x: number, y: number }>>({});
  
  const updateLoraSelection = (nodeId: string, updates: any) => {
    setLoraSelections(prev => {
      const current = prev[nodeId];
      const normalized = typeof current === 'string' ? { list: current, mode: 'list' } : (current || { list: '', mode: 'list' });
      return { ...prev, [nodeId]: { ...normalized, ...updates } };
    });
  };

  // LoRA Studio State
  const [loraFiles, setLoraFiles] = useState<any[]>([]);
  const [editingLoraFile, setEditingLoraFile] = useState<any>(null);
  const [loraPage, setLoraPage] = useState(0);

  // Initialize
  useEffect(() => {
    fetch('/api/config').then(res => res.json()).then(data => setConfig(data.config || data));
    fetch('/api/workflows').then(res => res.json()).then(data => setWorkflows(data.workflows || []));
    fetch('/api/loras').then(res => res.json()).then(data => setLoraFiles(data.loras || []));
  }, []);

  const saveConfig = async (newConfig: any) => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: newConfig })
      });
      if (!res.ok) throw new Error('Failed to save');
      setConfig(newConfig);
      alert('Settings saved successfully!');
    } catch (e) {
      alert('Failed to save settings');
    }
  };

  const loadWorkflow = async (wf: any) => {
    try {
      const res = await fetch('/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'load', jsonPath: wf.path })
      });
      const data = await res.json();
      setSelectedWorkflow({ ...wf, content: data.workflow, manifest: data.manifest });
      setObjectInfo(data.objectInfo);
      let loadedSelections = data.manifest?.discord?.inputs;
      if ((!loadedSelections || loadedSelections.length === 0) && data.manifest?.mapping && data.manifest?.inputs) {
        loadedSelections = data.manifest.inputs.map((inp: any) => {
          const mapData = data.manifest.mapping[inp.id];
          return {
            id: inp.id,
            nodeId: mapData ? String(mapData[0]) : '',
            field: mapData ? String(mapData[2]) : inp.id,
            type: inp.type,
            label: inp.label || inp.id,
            required: inp.required !== false,
            choices: inp.choices
          };
        });
      }
      // Normalize types in loaded selections: apply inferDiscordType so
      // any old/wrong types (e.g. 'string' for audio) are corrected immediately
      // when the user opens the workflow in the Architect.
      if (Array.isArray(loadedSelections) && data.workflow && data.objectInfo) {
        loadedSelections = loadedSelections.map((sel: any) => {
          const nodeClassType = data.workflow?.[sel.nodeId]?.class_type || '';
          const inferred = inferDiscordType(nodeClassType, sel.field, data.objectInfo, sel.type);
          
          // Force upgrade to upload types if inferred, or use inferred if generic
          const genericTypes = ['string', 'text', 'STRING', 'number', 'NUMBER', ''];
          const isGeneric = genericTypes.includes(sel.type);
          const isUpload = inferred.type.endsWith('_upload');
          
          const normalizedType = (isGeneric || isUpload) ? inferred.type : sel.type;
          
          return {
            ...sel,
            type: normalizedType,
            choices: normalizedType === 'select' ? (sel.choices || inferred.choices) : undefined
          };
        });
      }
      setSelections(loadedSelections || []);
      const fallbackName = wf.name.replace(/\.json$/i, '').toLowerCase();
      setCustomCommandName(data.manifest?.discord_command || data.manifest?.discord?.command || fallbackName);
      setLoraSelections(data.manifest?.discord?.loras || {});
      if (data.manifest?.discord?.ui) {
        setUiConfig(data.manifest.discord.ui);
        if (data.manifest.discord.ui.positions) {
          setNodeCoords(data.manifest.discord.ui.positions);
        } else {
          setNodeCoords({}); // Reset if no positions
        }
      } else {
        setNodeCoords({});
      }
    } catch (e) {
      console.error('Failed to load workflow:', e);
    }
  };

  const updateWorkflowInput = (nodeId: string, field: string, value: any) => {
    if (!selectedWorkflow) return;
    const wf = { ...selectedWorkflow };
    wf.content = { ...wf.content };
    wf.content[nodeId] = { ...wf.content[nodeId] };
    wf.content[nodeId].inputs = { ...wf.content[nodeId].inputs, [field]: value };
    setSelectedWorkflow(wf);
  };

  const importWorkflow = async (filename: string, workflow: any) => {
    try {
      const res = await fetch('/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'import', filename, workflow })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      
      // Refresh workflow list
      const listRes = await fetch('/api/workflows');
      const listData = await listRes.json();
      setWorkflows(listData.workflows || []);
      
      alert('Workflow imported successfully!');
    } catch (e: any) {
      alert(`Failed to import: ${e.message}`);
    }
  };

  const deleteWorkflow = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete ${filename}? This will also remove its manifest.`)) return;
    try {
      const res = await fetch('/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'delete', filename })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      
      setSelectedWorkflow(null);
      setSelections([]);
      
      // Refresh list
      const listRes = await fetch('/api/workflows');
      const listData = await listRes.json();
      setWorkflows(listData.workflows || []);
      
    } catch (e: any) {
      alert(`Failed to delete: ${e.message}`);
    }
  };

  const saveWorkflow = async () => {
    if (!selectedWorkflow) return;
    try {
      const rootMapping: any = {};
      const rootInputs: any[] = [];
      
      selections.forEach((sel) => {
        const inputId = sel.id || `${sel.field}_${sel.nodeId}`.replace(/[^a-zA-Z0-9_]/g, '');
        rootMapping[inputId] = [sel.nodeId, "inputs", sel.field];
        
        const inputObj: any = {
          id: inputId,
          type: sel.type || 'string',
          label: sel.label || sel.field,
          required: sel.required !== false
        };
        
        if (sel.type === 'select') {
           if (sel.choices) {
               inputObj.choices = sel.choices;
           } else {
               const nodeInfo = objectInfo?.[selectedWorkflow?.content?.[sel.nodeId]?.class_type];
               const inputInfo = nodeInfo?.input?.required?.[sel.field] || nodeInfo?.input?.optional?.[sel.field];
               if (Array.isArray(inputInfo) && Array.isArray(inputInfo[0])) {
                   inputObj.choices = inputInfo[0];
               }
           }
        }
        rootInputs.push(inputObj);
      });

      const manifest = {
        ...(selectedWorkflow.manifest || {}),
        workflow_name: selectedWorkflow.name.replace(/\.json$/i, ''), // e.g. "FluxDev"
        discord_command: customCommandName || selectedWorkflow.name.replace(/\.json$/i, '').toLowerCase(),
        description: (selectedWorkflow.manifest?.description) || `Run ${customCommandName || selectedWorkflow.name.replace(/\.json$/i, '')} workflow`,
        mapping: rootMapping,
        inputs: rootInputs,
        discord: {
          command: customCommandName || selectedWorkflow.name.replace(/\.json$/i, '').toLowerCase(),
          inputs: selections.map(s => {
            const { choices, ...rest } = s;
            return s.type === 'select' ? s : rest;
          }),
          ui: {
            ...uiConfig,
            positions: nodeCoords
          },
          loras: loraSelections
        }
      };
      await fetch('/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          action: 'save', 
          filename: selectedWorkflow.name, 
          manifest,
          workflow: selectedWorkflow.content
        })
      });
      alert('Workflow saved successfully!');
    } catch (e) {
      alert('Failed to save workflow');
    }
  };

  const toggleInput = (nodeId: string, field: string, type: string | null) => {
    const existing = selections.find(s => s.nodeId === nodeId && s.field === field);
    if (existing) {
      setSelections(selections.filter(s => s !== existing));
    } else if (type !== null) {
      const classType = selectedWorkflow?.content?.[nodeId]?.class_type || '';
      const { type: inferredType, choices } = inferDiscordType(classType, field, objectInfo);
      setSelections([...selections, {
        id: field,
        nodeId,
        field,
        type: inferredType,
        label: field,
        required: true,
        choices
      }]);
    }
  };

  const updateSelection = (idx: number, updates: any) => {
    const newSels = [...selections];
    newSels[idx] = { ...newSels[idx], ...updates };
    setSelections(newSels);
  };

  const moveInput = (idx: number, dir: 'up' | 'down') => {
    if (dir === 'up' && idx === 0) return;
    if (dir === 'down' && idx === selections.length - 1) return;
    const newSels = [...selections];
    const target = dir === 'up' ? idx - 1 : idx + 1;
    [newSels[idx], newSels[target]] = [newSels[target], newSels[idx]];
    setSelections(newSels);
  };

  const loadLoraFile = async (file: any) => {
    try {
      const res = await fetch('/api/loras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'load', filename: file.name })
      });
      const data = await res.json();
      setEditingLoraFile({ name: file.name, content: data.data.available_loras || data.data });
      setLoraPage(0);
    } catch (e) {
      console.error('Failed to load LoRA file:', e);
    }
  };

  const saveLoraFile = async () => {
    if (!editingLoraFile) return;
    try {
      await fetch('/api/loras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          action: 'save', 
          filename: editingLoraFile.name, 
          data: { available_loras: editingLoraFile.content }
        })
      });
      alert('LoRA list saved successfully!');
    } catch (e) {
      alert('Failed to save LoRA list');
    }
  };

  const updateLoraField = (idx: number, field: string, value: any) => {
    if (!editingLoraFile) return;
    const newContent = [...editingLoraFile.content];
    newContent[idx] = { ...newContent[idx], [field]: value };
    setEditingLoraFile({ ...editingLoraFile, content: newContent });
  };

  const moveLora = (idx: number, dir: 'up' | 'down') => {
    if (!editingLoraFile) return;
    if (dir === 'up' && idx === 0) return;
    if (dir === 'down' && idx === editingLoraFile.content.length - 1) return;
    const newContent = [...editingLoraFile.content];
    const target = dir === 'up' ? idx - 1 : idx + 1;
    [newContent[idx], newContent[target]] = [newContent[target], newContent[idx]];
    setEditingLoraFile({ ...editingLoraFile, content: newContent });
  };

  const deleteLora = (idx: number) => {
    if (!editingLoraFile) return;
    const newContent = [...editingLoraFile.content];
    newContent.splice(idx, 1);
    setEditingLoraFile({ ...editingLoraFile, content: newContent });
  };

  const addLora = (initialData: any = {}) => {
    if (!editingLoraFile) return;
    const newContent = [...editingLoraFile.content];
    newContent.push({
      file: "new_lora.safetensors",
      name: "New LoRA",
      weight: 1.0,
      add_prompt: "",
      url: "",
      category: "",
      description: "",
      is_active: true,
      ...initialData
    });
    setEditingLoraFile({ ...editingLoraFile, content: newContent });
  };
  const createNewLoraList = async () => {
    const name = prompt("Enter new list name (e.g. cinematic_styles):");
    if (!name) return;
    
    try {
      const res = await fetch('/api/loras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create', filename: name })
      });
      if (res.ok) {
        // We need a way to refresh. refreshLoraLists is not exported but we can just reload the page or add it.
        // Actually, let's just use the current fetch logic.
        const listRes = await fetch('/api/loras');
        const listData = await listRes.json();
        setLoraFiles(listData.loras || []);
        
        const fname = name.endsWith('.json') ? name : `${name}.json`;
        loadLoraFile({ name: fname, path: fname });
      } else {
        const err = await res.json();
        alert(err.error || 'Failed to create list');
      }
    } catch (e) {
      alert('Error creating list');
    }
  };

  const deleteLoraList = async (file: any) => {
    if (!confirm(`Are you sure you want to delete ${file.name}? This cannot be undone.`)) return;
    
    try {
      const res = await fetch('/api/loras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'delete_file', filename: file.name })
      });
      if (res.ok) {
        if (editingLoraFile?.name === file.name) {
          setEditingLoraFile(null);
        }
        const listRes = await fetch('/api/loras');
        const listData = await listRes.json();
        setLoraFiles(listData.loras || []);
      } else {
        const err = await res.json();
        alert(err.error || 'Failed to delete list');
      }
    } catch (e) {
      alert('Error deleting list');
    }
  };

  const value = {
    activeTab, setActiveTab,
    viewMode, setViewMode,
    config, setConfig, saveConfig,
    workflows,
    selectedWorkflow, setSelectedWorkflow,
    selections, setSelections,
    customCommandName, setCustomCommandName,
    uiConfig, setUiConfig,
    loraFiles, setLoraFiles,
    editingLoraFile, setEditingLoraFile,
    loraPage, setLoraPage,
    loadWorkflow, saveWorkflow, importWorkflow, deleteWorkflow,
    toggleInput, updateSelection, moveInput,
    loadLoraFile, saveLoraFile, updateLoraField, moveLora, deleteLora, addLora,
    createNewLoraList, deleteLoraList,
    loraSelections, setLoraSelections, updateLoraSelection,
    objectInfo, updateWorkflowInput,
    nodeCoords, setNodeCoords
  };

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
}
