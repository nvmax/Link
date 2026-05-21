"use client";
// UPDATED: Workflow Node Auto-Installation Logic Integrated

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { X, CheckCircle2, AlertCircle, Info } from 'lucide-react';

let globalApiKey: string | null = null;

export type ToastType = 'success' | 'error' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
}

interface DashboardContextType {
  showToast: (msg: string, type?: ToastType) => void;
  activeTab: 'setup' | 'architect' | 'modal-studio' | 'lora-studio' | 'ai-studio' | 'role-studio';
  setActiveTab: (tab: 'setup' | 'architect' | 'modal-studio' | 'lora-studio' | 'ai-studio' | 'role-studio') => void;
  viewMode: 'list' | 'visual';
  setViewMode: (mode: 'list' | 'visual') => void;
  config: any;
  isConfigLoaded: boolean;
  setConfig: (config: any) => void;
  saveConfig: (newConfig: any) => Promise<void>;
  workflows: any[];
  selectedWorkflow: any;
  setSelectedWorkflow: (wf: any) => void;
  selections: any[];
  setSelections: (selections: any[]) => void;
  customCommandName: string;
  setCustomCommandName: (name: string) => void;
  displayName: string;
  setDisplayName: (name: string) => void;
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
  importWorkflow: (filename: string, workflow: any, force?: boolean) => Promise<void>;
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
  missingNodes: string[];
  setMissingNodes: (nodes: string[]) => void;
  isInstalling: boolean;
  handleNodeInstall: () => Promise<void>;
  pendingImport: { name: string, workflow: any } | null;
  setPendingImport: (imp: { name: string, workflow: any } | null) => void;
  pendingLoad: boolean;
  setPendingLoad: (v: boolean) => void;
  missingModels: any[];
  setMissingModels: (models: any[]) => void;
  isDownloadingModels: boolean;
  modelDownloadProgress: Record<string, string>;
  modelDownloadStats: Record<string, any>;
  handleModelDownload: (modelsWithRepos: any[]) => Promise<void>;
  handleRetrySingleModel: (model: any) => Promise<void>;
  handleReboot: () => Promise<void>;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  aiConfig: any;
  setAiConfig: (config: any) => void;
  saveAiConfig: (newConfig: any) => Promise<void>;
  systemPrompts: any[];
  setSystemPrompts: (prompts: any[]) => void;
  saveSystemPrompts: (prompts: any[]) => Promise<void>;
  aiPrompt: any;
  setAiPrompt: (prompt: any) => void;
  activeTheme: string;
  setActiveTheme: (theme: string) => void;
  customThemeColors: Record<string, string>;
  setCustomThemeColors: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  customCss: string;
  setCustomCss: (css: string) => void;
  isThemeModalOpen: boolean;
  setIsThemeModalOpen: (open: boolean) => void;
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

  // 4. ComfyUI objectInfo — Number types (INT, FLOAT) → number
  if (Array.isArray(inputInfo) && (inputInfo[0] === 'INT' || inputInfo[0] === 'FLOAT' || inputInfo[0] === 'NUMBER')) {
    return { type: 'number' };
  }

  // 5. If existing type is already a valid upload type, keep it
  if (existingType && ['image_upload', 'audio_upload', 'video_upload', 'select', 'number'].includes(existingType)) {
    return { type: existingType };
  }

  // Default — free text
  return { type: 'text' };
}

function getPrimaryField(classType: string): string | null {
  const c = classType.toLowerCase();
  if (c.includes('unetloader')) return 'unet_name';
  if (c.includes('checkpointloader')) return 'ckpt_name';
  if (c.includes('cliptextencode')) return 'text';
  if (c.includes('loraloader')) return 'lora_name';
  if (c.includes('vaeloader')) return 'vae_name';
  if (c.includes('upscalemodel')) return 'model_name';
  if (c.includes('controlnetloader')) return 'control_net_name';
  if (c.includes('empty潜') || c.includes('emptylatent')) return 'width'; // or batch_size
  return null;
}

export const THEME_PRESETS: Record<string, {
  name: string;
  colors: Record<string, string>;
}> = {
  'classic-dark': {
    name: 'Classic Dark',
    colors: {
      'bg-primary': '#0a0a0c',
      'bg-sidebar': '#0d0d0f',
      'bg-card': '#111114',
      'text-primary': '#f1f5f9',
      'text-secondary': '#94a3b8',
      'accent-primary': '#6366f1',
      'accent-hover': '#4f46e5',
      'border-color': 'rgba(255, 255, 255, 0.05)',
      'accent-glow': 'rgba(99, 102, 241, 0.15)'
    }
  },
  'sunset-cyberpunk': {
    name: 'Sunset Cyberpunk',
    colors: {
      'bg-primary': '#07020d',
      'bg-sidebar': '#0c0418',
      'bg-card': '#120724',
      'text-primary': '#f8fafc',
      'text-secondary': '#a78bfa',
      'accent-primary': '#ec4899',
      'accent-hover': '#db2777',
      'border-color': 'rgba(236, 72, 153, 0.15)',
      'accent-glow': 'rgba(236, 72, 153, 0.25)'
    }
  },
  'emerald-matrix': {
    name: 'Emerald Matrix',
    colors: {
      'bg-primary': '#020604',
      'bg-sidebar': '#050e09',
      'bg-card': '#08160e',
      'text-primary': '#ecfdf5',
      'text-secondary': '#34d399',
      'accent-primary': '#10b981',
      'accent-hover': '#059669',
      'border-color': 'rgba(16, 185, 129, 0.15)',
      'accent-glow': 'rgba(16, 185, 129, 0.25)'
    }
  },
  'sunset-glow': {
    name: 'Sunset Glow',
    colors: {
      'bg-primary': '#0f0907',
      'bg-sidebar': '#180e0a',
      'bg-card': '#20140f',
      'text-primary': '#fff7ed',
      'text-secondary': '#fdba74',
      'accent-primary': '#f97316',
      'accent-hover': '#ea580c',
      'border-color': 'rgba(249, 115, 22, 0.15)',
      'accent-glow': 'rgba(249, 115, 22, 0.25)'
    }
  },
  'nordic-cold': {
    name: 'Nordic Cold',
    colors: {
      'bg-primary': '#0f172a',
      'bg-sidebar': '#1e293b',
      'bg-card': '#334155',
      'text-primary': '#f8fafc',
      'text-secondary': '#cbd5e1',
      'accent-primary': '#38bdf8',
      'accent-hover': '#0ea5e9',
      'border-color': 'rgba(56, 189, 248, 0.15)',
      'accent-glow': 'rgba(56, 189, 248, 0.2)'
    }
  },
  'clean-light': {
    name: 'Clean Light (Snow)',
    colors: {
      'bg-primary': '#f8fafc',
      'bg-sidebar': '#ffffff',
      'bg-card': '#f1f5f9',
      'text-primary': '#0f172a',
      'text-secondary': '#475569',
      'accent-primary': '#4f46e5',
      'accent-hover': '#3730a3',
      'border-color': 'rgba(0, 0, 0, 0.08)',
      'accent-glow': 'rgba(79, 70, 229, 0.15)'
    }
  }
};

function ThemeEngineStyles({
  theme,
  customColors,
  customCss
}: {
  theme: string;
  customColors: Record<string, string>;
  customCss: string;
}) {
  const colors = theme === 'custom' ? customColors : (THEME_PRESETS[theme]?.colors || THEME_PRESETS['classic-dark'].colors);

  const styleText = `
    :root {
      --bg-primary: ${colors['bg-primary']};
      --bg-sidebar: ${colors['bg-sidebar']};
      --bg-card: ${colors['bg-card']};
      --text-primary: ${colors['text-primary']};
      --text-secondary: ${colors['text-secondary']};
      --accent-primary: ${colors['accent-primary']};
      --accent-hover: ${colors['accent-hover']};
      --border-color: ${colors['border-color']};
      --accent-glow: ${colors['accent-glow']};

      --background: ${colors['bg-primary']};
      --foreground: ${colors['text-primary']};
    }
    
    ::selection {
      background-color: ${colors['accent-glow']};
    }
    
    ${customCss}
  `;

  return <style id="link-theme-custom-styles" dangerouslySetInnerHTML={{ __html: styleText }} />;
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState<'setup' | 'architect' | 'modal-studio' | 'lora-studio' | 'ai-studio' | 'role-studio'>('setup');
  const [isConfigLoaded, setIsConfigLoaded] = useState<boolean>(false);
  
  // Theme Engine States
  const [activeTheme, setActiveTheme] = useState<string>('classic-dark');
  const [customThemeColors, setCustomThemeColors] = useState<Record<string, string>>({
    'bg-primary': '#0a0a0c',
    'bg-sidebar': '#0d0d0f',
    'bg-card': '#111114',
    'text-primary': '#f1f5f9',
    'text-secondary': '#94a3b8',
    'accent-primary': '#6366f1',
    'accent-hover': '#4f46e5',
    'border-color': 'rgba(255, 255, 255, 0.05)',
    'accent-glow': 'rgba(99, 102, 241, 0.15)'
  });
  const [customCss, setCustomCss] = useState<string>('');
  const [isThemeModalOpen, setIsThemeModalOpen] = useState<boolean>(false);

  // Load Theme State on Init
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('link-theme');
      if (savedTheme) setActiveTheme(savedTheme);

      const savedColors = localStorage.getItem('link-theme-custom-colors');
      if (savedColors) {
        try {
          setCustomThemeColors(JSON.parse(savedColors));
        } catch (_) {}
      }

      const savedCss = localStorage.getItem('link-theme-custom-css');
      if (savedCss) setCustomCss(savedCss);
    }
  }, []);

  // Save Theme State on Changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('link-theme', activeTheme);
      localStorage.setItem('link-theme-custom-colors', JSON.stringify(customThemeColors));
      localStorage.setItem('link-theme-custom-css', customCss);
    }
  }, [activeTheme, customThemeColors, customCss]);

  const [viewMode, setViewMode] = useState<'list' | 'visual'>('list');
  const [config, setConfig] = useState<any>({});
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null);
  const [objectInfo, setObjectInfo] = useState<any>(null);
  const [selections, setSelections] = useState<any[]>([]);
  const [customCommandName, setCustomCommandName] = useState<string>('');
  const [displayName, setDisplayName] = useState<string>('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const toggleSidebar = () => setIsSidebarOpen(prev => !prev);

  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const [uiConfig, setUiConfig] = useState<any>({
    embed: {
      title_template: "{user}'s Generation",
      color: "#5865F2",
      use_role_color: true,
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
  
  const [missingNodes, setMissingNodes] = useState<string[]>([]);
  const [pendingImport, setPendingImport] = useState<{ name: string, workflow: any } | null>(null);
  const [pendingLoad, setPendingLoad] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);
  
  const [missingModels, setMissingModels] = useState<any[]>([]);
  const [isDownloadingModels, setIsDownloadingModels] = useState(false);
  const [modelDownloadProgress, setModelDownloadProgress] = useState<Record<string, string>>({});
  const [modelDownloadStats, setModelDownloadStats] = useState<Record<string, any>>({});
  
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isDownloadingModels) {
      interval = setInterval(async () => {
        try {
          const res = await fetch('http://127.0.0.1:8001/api/models/progress');
          if (res.ok) {
            const data = await res.json();
            setModelDownloadStats(data);
          }
        } catch (e) {
          // Ignore network errors during polling
        }
      }, 500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isDownloadingModels]);

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

  // AI Workflow Integration
  const [aiPrompt, setAiPrompt] = useState<any>({ enabled: false, category: 'image', prompt_id: '', target_input: '' });

  // AI Studio State
  const [aiConfig, setAiConfig] = useState<any>({});
  const [systemPrompts, setSystemPrompts] = useState<any[]>([]);

  // Initialize
  useEffect(() => {
    // Override window.fetch globally to intercept and inject the X-API-Key header to the local API server
    const originalFetch = window.fetch;
    window.fetch = async (input, init) => {
      let url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : (input as Request).url;
      
      if (url.includes('127.0.0.1:8001/api') || url.includes('localhost:8001/api')) {
        if (globalApiKey) {
          init = init || {};
          const headers = new Headers(init.headers || {});
          if (!headers.has('X-API-Key')) {
            headers.set('X-API-Key', globalApiKey);
          }
          init.headers = headers;
        }
      }
      return originalFetch(input, init);
    };

    // Load main application configuration from .env first, then initialize direct API requests
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        const parsedConfig = data.config || data;
        setConfig(parsedConfig);
        globalApiKey = parsedConfig.API_KEY || null;

        // Perform requests that target the API Server (Port 8001)
        fetch('http://127.0.0.1:8001/api/ai/config')
          .then(res => res.json())
          .then(data => setAiConfig(data))
          .catch(err => console.warn('Failed to fetch AI config:', err));
          
        fetch('http://127.0.0.1:8001/api/ai/prompts')
          .then(res => res.json())
          .then(data => setSystemPrompts(data))
          .catch(err => console.warn('Failed to fetch system prompts:', err));

        setIsConfigLoaded(true);
      })
      .catch(err => {
        console.warn('Failed to load application config:', err);
        setIsConfigLoaded(true);
      });

    fetch('/api/workflows').then(res => res.json()).then(data => setWorkflows(data.workflows || []));
    fetch('/api/loras').then(res => res.json()).then(data => setLoraFiles(data.loras || []));

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  const saveAiConfig = async (newConfig: any) => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/ai/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      if (!res.ok) throw new Error('Failed to save AI config');
      setAiConfig(newConfig);
    } catch (e) {
      console.error(e);
      showToast('Failed to save AI configuration', 'error');
    }
  };

  const saveSystemPrompts = async (newPrompts: any[]) => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/ai/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPrompts)
      });
      if (!res.ok) throw new Error('Failed to save system prompts');
      setSystemPrompts(newPrompts);
    } catch (e) {
      console.error(e);
      showToast('Failed to save system prompts', 'error');
    }
  };

  const saveConfig = async (newConfig: any) => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: newConfig })
      });
      if (!res.ok) throw new Error('Failed to save');
      
      setConfig(newConfig);
      globalApiKey = newConfig.API_KEY || null;

      // Tell the Python backend to hot-reload .env so Config values update immediately
      try {
        await fetch('http://127.0.0.1:8001/api/config/reload', { method: 'POST' });
      } catch (_) {
        // Non-fatal — bot may not be running yet
      }

      showToast('Settings saved successfully!', 'success');
    } catch (e) {
      showToast('Failed to save settings', 'error');
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

      // ── Health Check on Click ─────────────────────────────────────────────
      // For pre-bundled workflows (those that already exist in src/workflows)
      // we run the same node + model validation that happens during import,
      // but only when the user explicitly clicks the workflow. Nothing happens
      // at bot startup. If something is missing the modals pop up; once the
      // user resolves them (install / download) we simply display the workflow
      // that is already loaded — no re-import needed.
      if (data.workflow && data.objectInfo) {
        const nodeTypes = new Set(Object.values(data.workflow).map((n: any) => n.class_type));
        const missing = Array.from(nodeTypes).filter(type => !data.objectInfo[type]) as string[];
        if (missing.length > 0) {
          console.log('[loadWorkflow] Missing nodes detected:', missing);
          setMissingNodes(missing);
          // Store the workflow in pendingImport so handleNodeInstall can use it,
          // but mark pendingLoad=true so we skip executeImport afterwards.
          setPendingImport({ name: wf.name, workflow: data.workflow });
          setPendingLoad(true);
          // Still apply the loaded state so the canvas shows up after resolution
          setSelectedWorkflow({ ...wf, content: data.workflow, manifest: data.manifest });
          setObjectInfo(data.objectInfo);
          // Fall through to populate selections etc. so the view is ready
        } else {
          // No missing nodes — check models
          try {
            const modelCheckRes = await fetch('http://127.0.0.1:8001/api/models/check', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data.workflow)
            });
            if (modelCheckRes.ok) {
              const modelData = await modelCheckRes.json();
              const missingMods = modelData.missing || [];
              if (missingMods.length > 0) {
                console.log('[loadWorkflow] Missing models detected:', missingMods);
                setMissingModels(missingMods);
                setPendingImport({ name: wf.name, workflow: data.workflow });
                setPendingLoad(true);
              }
            }
          } catch (e) {
            console.warn('[loadWorkflow] Model check failed (backend may be offline):', e);
          }
        }
      }
      // ──────────────────────────────────────────────────────────────────────

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
      setDisplayName(data.manifest?.display_name || data.manifest?.workflow_name || '');
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
      setAiPrompt(data.manifest?.ai_prompt || { enabled: false, category: 'image', prompt_id: '', target_input: '' });
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

  const checkModelsBeforeImport = async (filename: string, workflow: any) => {
    try {
      const modelCheckRes = await fetch('http://127.0.0.1:8001/api/models/check', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify(workflow)
      });
      if (modelCheckRes.ok) {
         const modelData = await modelCheckRes.json();
         const missingMods = modelData.missing || [];
         if (missingMods.length > 0) {
           console.log('Missing models detected:', missingMods);
           setMissingModels(missingMods);
           setPendingImport({ name: filename, workflow });
           return false;
         }
      }
      return true;
    } catch (e) {
       console.error("Failed model check", e);
       return true; // proceed anyway if backend is down
    }
  };

  const importWorkflow = async (filename: string, workflow: any, force: boolean = false) => {
    try {
      // 1. Discovery Phase: Check for missing nodes before importing
      if (!force) {
        if (objectInfo) {
          const nodeTypes = new Set(Object.values(workflow).map((n: any) => n.class_type));
          const missing = Array.from(nodeTypes).filter(type => !objectInfo[type]) as string[];
          
          if (missing.length > 0) {
            console.log('Missing nodes detected:', missing);
            setMissingNodes(missing);
            setPendingImport({ name: filename, workflow });
            return; // Stop and wait for user approval via modal
          }
        }
        
        // 1.5. Discovery Phase: Check for missing models
        const modelsOk = await checkModelsBeforeImport(filename, workflow);
        if (!modelsOk) return;
      }

      await executeImport(filename, workflow);
    } catch (e: any) {
      showToast(`Failed to import: ${e.message}`, 'error');
    }
  };

  const executeImport = async (filename: string, workflow: any) => {
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
    
    showToast('Workflow imported successfully!', 'success');
  };

  const handleReboot = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/comfy/reboot', {
        method: 'POST'
      });
      const data = await res.json();
      if (data.status === 'success') {
        showToast("ComfyUI reboot signal sent. Please wait a few moments for it to restart.");
      } else {
        showToast(`Reboot failed: ${data.message}. You may need to manually restart ComfyUI.`, 'error');
      }
    } catch (e: any) {
      console.error('Reboot error:', e);
      showToast(`Reboot failed: ${e.message}`, 'error');
    }
  };

  const handleNodeInstall = async () => {
    if (!pendingImport) return;
    setIsInstalling(true);
    try {
      // Use the Python backend (port 8001) for the heavy lifting
      const res = await fetch('http://127.0.0.1:8001/api/comfy/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow: pendingImport.workflow,
          missing_nodes: missingNodes
        })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Installation failed');

      showToast("Nodes installed successfully. Sending reboot signal to ComfyUI...", 'success');
      await handleReboot();
      
      // Re-fetch object info from the Next.js API (which fetches from ComfyUI)
      // This ensures the Architect sees the new nodes.
      const refreshRes = await fetch('/api/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'load', jsonPath: '' }) // Generic load to trigger object_info refresh
      });
      const refreshData = await refreshRes.json();
      if (refreshData.objectInfo) {
        setObjectInfo(refreshData.objectInfo);
      }

      if (pendingLoad) {
        // Triggered from loadWorkflow (pre-bundled workflow) — workflow is already
        // displayed; just check models then close the modal without re-importing.
        const modelsOk = await checkModelsBeforeImport(pendingImport.name, pendingImport.workflow);
        if (modelsOk) {
          setPendingImport(null);
          setPendingLoad(false);
        }
      } else {
        // Triggered from importWorkflow — finalize the import.
        const modelsOk = await checkModelsBeforeImport(pendingImport.name, pendingImport.workflow);
        if (modelsOk) {
          await executeImport(pendingImport.name, pendingImport.workflow);
          setPendingImport(null);
        }
      }
      
      setMissingNodes([]);
    } catch (e: any) {
      console.error('Node installation error:', e);
      showToast(`Installation failed: ${e.message}`, 'error');
    } finally {
      setIsInstalling(false);
    }
  };

  const downloadSingleModel = async (model: any) => {
    setModelDownloadProgress(prev => ({ ...prev, [model.filename]: 'downloading' }));
    try {
      const res = await fetch('http://127.0.0.1:8001/api/models/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(model)
      });
      if (res.status === 403) {
         setModelDownloadProgress(prev => ({ ...prev, [model.filename]: 'gated' }));
         return false;
      }
      if (!res.ok) throw new Error("Failed");
      
      setModelDownloadProgress(prev => ({ ...prev, [model.filename]: 'done' }));
      return true;
    } catch (e) {
      setModelDownloadProgress(prev => ({ ...prev, [model.filename]: 'error' }));
      return false;
    }
  };

  const handleModelDownload = async (modelsWithRepos: any[]) => {
    setIsDownloadingModels(true);
    let allSuccess = true;
    for (const m of modelsWithRepos) {
      if (m.manuallyResolved || modelDownloadProgress[m.filename] === 'done') {
         setModelDownloadProgress(prev => ({ ...prev, [m.filename]: 'done' }));
         continue;
      }
      if (!m.repo_id) {
         setModelDownloadProgress(prev => ({ ...prev, [m.filename]: 'error' }));
         allSuccess = false;
         continue;
      }
      const success = await downloadSingleModel(m);
      if (!success) allSuccess = false;
    }
    
    setIsDownloadingModels(false);
    
    if (allSuccess) {
      showToast("Models downloaded successfully. Sending reboot signal to ComfyUI...", 'success');
      await handleReboot();
      
      if (pendingImport) {
        if (pendingLoad) {
          // Triggered from loadWorkflow — workflow already displayed, just close.
          setPendingImport(null);
          setPendingLoad(false);
        } else {
          // Triggered from importWorkflow — finalize the import.
          await executeImport(pendingImport.name, pendingImport.workflow);
          setPendingImport(null);
        }
      }
    }
    
    setMissingModels([]);
  };

  const handleRetrySingleModel = async (model: any) => {
    await downloadSingleModel(model);
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
      showToast(`Failed to delete: ${e.message}`, 'error');
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
        display_name: displayName,
        discord_command: customCommandName || selectedWorkflow.name.replace(/\.json$/i, '').toLowerCase(),
        ai_prompt: aiPrompt,
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
      showToast('Workflow saved successfully!', 'success');
    } catch (e) {
      showToast('Failed to save workflow', 'error');
    }
  };

  const toggleInput = (nodeId: string, field: string, type: string | null) => {
    // 1. Resolve "Smart Mapping" — if this is a link, follow it to the source node
    let targetNodeId = nodeId;
    let targetField = field;
    
    const nodeData = selectedWorkflow?.content?.[nodeId];
    const val = nodeData?.inputs?.[field];
    
    if (Array.isArray(val) && val.length >= 2) {
      const sourceNodeId = String(val[0]);
      const sourceNode = selectedWorkflow?.content?.[sourceNodeId];
      if (sourceNode) {
        const primary = getPrimaryField(sourceNode.class_type);
        if (primary) {
          targetNodeId = sourceNodeId;
          targetField = primary;
        }
      }
    }

    const existing = selections.find(s => s.nodeId === targetNodeId && s.field === targetField);
    if (existing) {
      setSelections(selections.filter(s => s !== existing));
    } else if (type !== null) {
      const classType = selectedWorkflow?.content?.[targetNodeId]?.class_type || '';
      const { type: inferredType, choices } = inferDiscordType(classType, targetField, objectInfo);
      setSelections([...selections, {
        id: targetField,
        nodeId: targetNodeId,
        field: targetField,
        type: inferredType,
        label: targetField,
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
      showToast('LoRA list saved successfully!', 'success');
    } catch (e) {
      showToast('Failed to save LoRA list', 'error');
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
        showToast(err.error || 'Failed to create list', 'error');
      }
    } catch (e) {
      showToast('Error creating list', 'error');
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
        showToast(err.error || 'Failed to delete list', 'error');
      }
    } catch (e) {
      showToast('Error deleting list', 'error');
    }
  };

  const value = {
    showToast,
    activeTab, setActiveTab,
    viewMode, setViewMode,
    config, isConfigLoaded, setConfig, saveConfig,
    workflows,
    selectedWorkflow, setSelectedWorkflow,
    selections, setSelections,
    customCommandName, setCustomCommandName,
    displayName, setDisplayName,
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
    nodeCoords, setNodeCoords,
    missingNodes, setMissingNodes,
    isInstalling, handleNodeInstall,
    pendingImport, setPendingImport,
    pendingLoad, setPendingLoad,
    missingModels, setMissingModels,
    isDownloadingModels, modelDownloadProgress, modelDownloadStats,
    handleModelDownload, handleRetrySingleModel, handleReboot,
    isSidebarOpen,
    setIsSidebarOpen,
    toggleSidebar,
    aiConfig,
    setAiConfig,
    saveAiConfig,
    systemPrompts,
    setSystemPrompts,
    saveSystemPrompts,
    aiPrompt,
    setAiPrompt,
    activeTheme, setActiveTheme,
    customThemeColors, setCustomThemeColors,
    customCss, setCustomCss,
    isThemeModalOpen, setIsThemeModalOpen
  };

  return (
    <DashboardContext.Provider value={value}>
        <ThemeEngineStyles theme={activeTheme} customColors={customThemeColors} customCss={customCss} />
        {children}
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
          {toasts.map(t => (
            <div key={t.id} className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border transition-all duration-300 animate-in slide-in-from-right-4 fade-in-0 ${
              t.type === 'success' ? 'bg-[#15191C]/90 backdrop-blur-md border-[#3B82F6]/30 text-white' :
              t.type === 'error' ? 'bg-red-950/90 backdrop-blur-md border-red-500/30 text-white' :
              'bg-[#15191C]/90 backdrop-blur-md border-[#23292F] text-white'
            }`}>
              {t.type === 'success' && <CheckCircle2 className="w-5 h-5 text-[#3B82F6]" />}
              {t.type === 'error' && <AlertCircle className="w-5 h-5 text-red-500" />}
              {t.type === 'info' && <Info className="w-5 h-5 text-zinc-400" />}
              <span className="text-sm font-medium">{t.message}</span>
              <button 
                onClick={() => setToasts(prev => prev.filter(x => x.id !== t.id))}
                className="ml-4 opacity-50 hover:opacity-100 transition-opacity"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
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
