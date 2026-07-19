"use client";

import React from 'react';
import { Network, Puzzle, Settings, Save, X, FolderSearch, RefreshCw, RotateCcw, ShieldCheck, History, Zap, CheckCircle2, AlertCircle, Check, Activity, PackagePlus, Loader2 } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

const autoDetectProvider = (value: string): string | null => {
  const clean = value.trim();
  if (clean.startsWith('sk-ant-')) return 'ANTHROPIC_API_KEY';
  if (clean.startsWith('AIzaSy')) return 'GEMINI_API_KEY';
  if (clean.startsWith('xai-')) return 'GROK_API_KEY';
  if (clean.startsWith('sk-') || clean.startsWith('sk-proj-')) return 'OPENAI_API_KEY';
  return null;
};

export function MissionControl() {
  const { config, setConfig, saveConfig, workflows, loraFiles, handleReboot, handleBotRestart, showToast, aiConfig } = useDashboard();

  const handleConfigChange = (key: string, value: string) => {
    setConfig({ ...config, [key]: value });
  };

  const [selectedAiKeyProvider, setSelectedAiKeyProvider] = React.useState('OPENAI_API_KEY');

  React.useEffect(() => {
    if (aiConfig?.active_provider) {
      const active = aiConfig.active_provider.toUpperCase();
      const providerKey = `${active}_API_KEY`;
      const validKeys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY', 'GROK_API_KEY', 'LMSTUDIO_API_KEY', 'OLLAMA_API_KEY', 'VLLM_API_KEY'];
      if (validKeys.includes(providerKey)) {
        setSelectedAiKeyProvider(providerKey);
        return;
      }
    }
    
    if (config) {
      if (config.GEMINI_API_KEY && !config.OPENAI_API_KEY) {
        setSelectedAiKeyProvider('GEMINI_API_KEY');
      } else if (config.ANTHROPIC_API_KEY && !config.OPENAI_API_KEY && !config.GEMINI_API_KEY) {
        setSelectedAiKeyProvider('ANTHROPIC_API_KEY');
      } else if (config.GROK_API_KEY && !config.OPENAI_API_KEY && !config.GEMINI_API_KEY && !config.ANTHROPIC_API_KEY) {
        setSelectedAiKeyProvider('GROK_API_KEY');
      }
    }
  }, [config, aiConfig]);
  const [newGuildId, setNewGuildId] = React.useState('');
  const [newChannelId, setNewChannelId] = React.useState('');
  const [managerType, setManagerType] = React.useState<'--enable-manager-legacy-ui' | '--enable-manager'>('--enable-manager');

  const handleAddGuild = () => {
    const val = newGuildId.trim();
    if (val) {
      const current = config.ALLOWED_GUILD_ID || '';
      const ids = current.split(',').filter(Boolean);
      if (!ids.includes(val)) {
        const next = current ? `${current},${val}` : val;
        handleConfigChange('ALLOWED_GUILD_ID', next);
      }
      setNewGuildId('');
    }
  };

  const handleAddChannel = () => {
    const val = newChannelId.trim();
    if (val) {
      const current = config.ALLOWED_CHANNEL_ID || '';
      const ids = current.split(',').filter(Boolean);
      if (!ids.includes(val)) {
        const next = current ? `${current},${val}` : val;
        handleConfigChange('ALLOWED_CHANNEL_ID', next);
      }
      setNewChannelId('');
    }
  };

  const handleSelectFolder = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8001/api/utils/select-folder', { method: 'POST' });
      const data = await res.json();
      if (data.path) {
        handleConfigChange('COMFY_PATH', data.path);
      }
    } catch (e) {
      console.error('Failed to open folder picker:', e);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
      <div className="p-8 rounded-3xl bg-gradient-to-br from-indigo-500/10 to-fuchsia-500/10 border border-white/5 relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[100px] -mr-32 -mt-32" />
        <h2 className="text-3xl font-black text-white mb-2 tracking-tight">Mission Control</h2>
        <p className="text-slate-400 leading-relaxed max-w-xl">Configure your ComfyUI integration and manage system-wide settings.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-500/20 flex items-center justify-center text-indigo-400"><Network className="w-5 h-5" /></div>
            <h3 className="font-bold text-white">ComfyUI Integration</h3>
          </div>
          <div className="space-y-4">
            <div className="grid gap-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Backend URL</label>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={config.COMFY_URL || 'http://127.0.0.1:8188'} 
                  onChange={(e) => handleConfigChange('COMFY_URL', e.target.value)}
                  className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-indigo-300 focus:border-indigo-500/50 outline-none transition-all" 
                />
                <button 
                  onClick={handleReboot}
                  className="bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 px-4 rounded-xl text-xs font-bold transition-all border border-rose-500/30 shrink-0 flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Restart
                </button>
              </div>
            </div>
            <div className="grid gap-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">ComfyUI File Path</label>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder="C:\Users\Admin\ComfyUI_windows_portable\ComfyUI"
                  value={config.COMFY_PATH || ''} 
                  onChange={(e) => handleConfigChange('COMFY_PATH', e.target.value)}
                  className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-indigo-300 focus:border-indigo-500/50 outline-none transition-all placeholder:text-white/10" 
                />
                <button 
                  onClick={handleSelectFolder}
                  className="bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-4 rounded-xl text-xs font-bold transition-all border border-indigo-500/30 flex items-center gap-2"
                >
                  <FolderSearch className="w-3.5 h-3.5" />
                  Select
                </button>
              </div>
              <p className="text-[9px] text-slate-600 mt-1 italic">Required for auto-installing nodes via comfy-cli.</p>
            </div>

          </div>
        </div>

        <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-fuchsia-500/20 flex items-center justify-center text-fuchsia-400"><Puzzle className="w-5 h-5" /></div>
            <h3 className="font-bold text-white">System Diagnostics</h3>
          </div>
          <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-xs text-slate-400 font-medium">Workflows Loaded</span>
                <span className="text-xs text-white font-bold">{workflows.length}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-xs text-slate-400 font-medium">LoRA Lists</span>
                <span className="text-xs text-white font-bold">{loraFiles.length}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-xs text-slate-400 font-medium">Discord Pipeline</span>
                <div className="flex items-center gap-2">
                  <BotStatus />
                  <button
                    id="btn-restart-bot"
                    onClick={handleBotRestart}
                    title="Restart Discord bot to pick up new slash commands"
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-[10px] font-black uppercase tracking-widest transition-all border border-indigo-500/20 hover:border-indigo-500/40 active:scale-95"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Restart
                  </button>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-xs text-slate-400 font-medium">ComfyUI Status</span>
                <ComfyStatusIndicator />
              </div>
          </div>
        </div>

        {/* Discord Activity (Inpainting) Card */}
        <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl md:col-span-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-fuchsia-500/20 flex items-center justify-center text-fuchsia-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white">Discord Activity (Interactive Inpainting)</h3>
              <p className="text-xs text-slate-500">Configure webserver domain and port for Discord Activities inpainting tool</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="grid gap-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Webserver Domain</label>
              <input 
                type="text" 
                placeholder="yourdomain.com"
                value={config.INPAINT_SERVER_DOMAIN || ''} 
                onChange={(e) => handleConfigChange('INPAINT_SERVER_DOMAIN', e.target.value)}
                className="bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-fuchsia-300 focus:border-fuchsia-500/50 outline-none transition-all placeholder:text-white/10" 
              />
            </div>
            <div className="grid gap-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Webserver Port</label>
              <input 
                type="number" 
                placeholder="8000"
                value={config.INPAINT_SERVER_PORT || '8000'} 
                onChange={(e) => handleConfigChange('INPAINT_SERVER_PORT', e.target.value)}
                className="bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-fuchsia-300 focus:border-fuchsia-500/50 outline-none transition-all" 
              />
            </div>
          </div>
        </div>
      </div>

      {/* ComfyUI Setup */}
      <SetupComfyUI managerType={managerType} setManagerType={setManagerType} />

      <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center text-amber-400"><Settings className="w-5 h-5" /></div>
            <div>
              <h3 className="font-bold text-white">Environment Configuration</h3>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">Manage .env variables</p>
            </div>
          </div>
          <button 
            onClick={() => saveConfig(config)}
            className="bg-amber-500 text-black px-6 py-2.5 rounded-xl font-black text-sm hover:bg-amber-400 transition-all shadow-xl shadow-amber-500/20 flex items-center justify-center gap-2 active:scale-95 shrink-0"
          >
            <Save className="w-4 h-4" /> Save Settings
          </button>
        </div>

        <div className="space-y-8 pt-4 border-t border-white/5">
          {/* Discord Access Management */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
            {/* Guild Management */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Whitelisted Servers</label>
                <span className="text-[10px] text-indigo-400 font-bold bg-indigo-500/10 px-2 py-0.5 rounded-full">{config.ALLOWED_GUILD_ID?.split(',').filter(Boolean).length || 0} Active</span>
              </div>
              
              <div className="space-y-3">
                {config.ALLOWED_GUILD_ID?.split(',').filter(Boolean).map((gid: string) => (
                  <GuildCard key={gid} id={gid} onRemove={(id) => {
                    const newIds = config.ALLOWED_GUILD_ID.split(',').filter((x: string) => x !== id).join(',');
                    handleConfigChange('ALLOWED_GUILD_ID', newIds);
                  }} />
                ))}
                
                  <div className="flex gap-2 p-2 bg-black/40 border border-white/5 rounded-2xl">
                    <input 
                      type="text"
                      placeholder="Enter Server ID..."
                      value={newGuildId}
                      onChange={(e) => setNewGuildId(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleAddGuild();
                        }
                      }}
                      className="flex-1 bg-transparent border-none px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600"
                    />
                    <button 
                      onClick={handleAddGuild}
                      className="bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-4 rounded-xl text-[10px] font-black uppercase transition-all"
                    >
                      Add
                    </button>
                  </div>
              </div>
            </div>

            {/* Channel Management */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Whitelisted Channels</label>
                <span className="text-[10px] text-fuchsia-400 font-bold bg-fuchsia-500/10 px-2 py-0.5 rounded-full">{config.ALLOWED_CHANNEL_ID?.split(',').filter(Boolean).length || 0} Active</span>
              </div>
              
              <div className="space-y-3">
                {config.ALLOWED_CHANNEL_ID?.split(',').filter(Boolean).map((cid: string) => (
                  <ChannelCard key={cid} id={cid} onRemove={(id) => {
                    const newIds = config.ALLOWED_CHANNEL_ID.split(',').filter((x: string) => x !== id).join(',');
                    handleConfigChange('ALLOWED_CHANNEL_ID', newIds);
                  }} />
                ))}
                
                  <div className="flex gap-2 p-2 bg-black/40 border border-white/5 rounded-2xl">
                    <input 
                      type="text"
                      placeholder="Enter Channel ID..."
                      value={newChannelId}
                      onChange={(e) => setNewChannelId(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleAddChannel();
                        }
                      }}
                      className="flex-1 bg-transparent border-none px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600"
                    />
                    <button 
                      onClick={handleAddChannel}
                      className="bg-fuchsia-500/10 hover:bg-fuchsia-500/20 text-fuchsia-400 px-4 rounded-xl text-[10px] font-black uppercase transition-all"
                    >
                      Add
                    </button>
                  </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-8 border-t border-white/5">
            <div className="space-y-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Discord Token</label>
              <input 
                type="password" 
                value={config.DISCORD_TOKEN || ''} 
                onChange={(e) => handleConfigChange('DISCORD_TOKEN', e.target.value)}
                placeholder="MTQ5NjI0MzYz..."
                className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-slate-300 focus:border-amber-500/50 outline-none transition-all placeholder:text-white/10" 
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Database URL</label>
              <input 
                type="text" 
                value={config.DATABASE_URL || 'sqlite:///data/link.db'} 
                onChange={(e) => handleConfigChange('DATABASE_URL', e.target.value)}
                className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-slate-300 focus:border-amber-500/50 outline-none transition-all" 
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">HuggingFace Token</label>
              <input 
                type="password" 
                value={config.HF_TOKEN || ''} 
                onChange={(e) => handleConfigChange('HF_TOKEN', e.target.value)}
                placeholder="hf_xxxxxxxx"
                className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-slate-300 focus:border-amber-500/50 outline-none transition-all placeholder:text-white/10" 
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <div className="flex items-center justify-between mb-2">
                <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">AI API Keys</label>
                <select 
                  value={selectedAiKeyProvider}
                  onChange={(e) => setSelectedAiKeyProvider(e.target.value)}
                  className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-2 py-1 text-[10px] font-black text-indigo-400 uppercase tracking-tighter outline-none cursor-pointer hover:bg-indigo-500/20 transition-all"
                >
                  <option value="OPENAI_API_KEY">OpenAI</option>
                  <option value="ANTHROPIC_API_KEY">Anthropic</option>
                  <option value="GEMINI_API_KEY">Gemini</option>
                  <option value="GROK_API_KEY">Grok</option>
                  <option value="LMSTUDIO_API_KEY">LM Studio</option>
                  <option value="OLLAMA_API_KEY">Ollama</option>
                  <option value="VLLM_API_KEY">vLLM</option>
                </select>
              </div>
              {['LMSTUDIO_API_KEY', 'OLLAMA_API_KEY', 'VLLM_API_KEY'].includes(selectedAiKeyProvider) ? (
                <div className="w-full bg-black/40 border border-emerald-500/10 rounded-xl px-4 py-3 text-sm text-emerald-400 font-medium">
                  {selectedAiKeyProvider === 'LMSTUDIO_API_KEY' && 'LM Studio runs locally and does not require an API key.'}
                  {selectedAiKeyProvider === 'OLLAMA_API_KEY' && 'Ollama runs locally and does not require an API key.'}
                  {selectedAiKeyProvider === 'VLLM_API_KEY' && 'vLLM runs locally and does not require an API key.'}
                </div>
              ) : (
                <input 
                  type="password" 
                  value={config[selectedAiKeyProvider] || ''} 
                  onChange={(e) => {
                    const val = e.target.value;
                    const detected = autoDetectProvider(val);
                    if (detected && detected !== selectedAiKeyProvider) {
                      setSelectedAiKeyProvider(detected);
                      const updatedConfig = { ...config };
                      delete updatedConfig[selectedAiKeyProvider];
                      updatedConfig[detected] = val;
                      setConfig(updatedConfig);
                    } else {
                      handleConfigChange(selectedAiKeyProvider, val);
                    }
                  }}
                  placeholder={`Enter ${selectedAiKeyProvider.replace('_', ' ')}...`}
                  className="w-full bg-black/40 border border-indigo-500/10 rounded-xl px-4 py-3 text-sm font-mono text-indigo-300 focus:border-indigo-500/50 outline-none transition-all placeholder:text-white/10 shadow-inner" 
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Node Management & Backups */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <NodeManager />
        </div>
        <div>
          <SnapshotManager />
        </div>
      </div>
    </div>
  );
}

function NodeItem({ node, isSelected, onToggle }: { node: any, isSelected: boolean, onToggle: () => void }) {
    return (
        <div 
            onClick={onToggle}
            className={`group flex items-center justify-between p-3 rounded-2xl border transition-all cursor-pointer ${
                isSelected 
                    ? 'bg-blue-500/10 border-blue-500/30 shadow-lg shadow-blue-500/5' 
                    : node.update_available 
                        ? 'bg-amber-500/5 border-amber-500/10 hover:border-amber-500/30' 
                        : 'bg-white/2 border-white/5 hover:border-white/10'
            }`}
        >
            <div className="flex items-center gap-3 min-w-0">
                <div className={`w-2 h-2 rounded-full shrink-0 ${
                    node.update_available 
                        ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)] animate-pulse' 
                        : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]'
                }`} />
                <div className="flex flex-col min-w-0">
                    <span className={`text-xs font-bold truncate transition-colors ${
                        isSelected ? 'text-blue-400' : node.update_available ? 'text-amber-200' : 'text-slate-200'
                    }`}>
                        {node.display_name}
                    </span>
                    <span className="text-[9px] text-slate-500 font-mono tracking-tight">
                        {node.author ? `${node.author} · ` : ''}{node.version}
                        {node.latest_version && node.latest_version !== node.version && (
                            <span className="text-amber-500/80 ml-1">→ {node.latest_version}</span>
                        )}
                    </span>
                </div>
            </div>
            
            <div className="flex items-center gap-2">
                {node.update_available && (
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                        <RefreshCw className="w-2.5 h-2.5 text-amber-500 animate-spin-slow" />
                        <span className="text-[10px] font-bold text-amber-500 uppercase tracking-tighter">Update</span>
                    </div>
                )}
                <div className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                    isSelected ? 'bg-blue-500 border-blue-500 scale-110' : 'border-white/10 group-hover:border-white/20'
                }`}>
                    {isSelected && <Check className="w-2.5 h-2.5 text-white" />}
                </div>
            </div>
        </div>
    );
}

function NodeManager() {
  const { handleReboot, showToast } = useDashboard();
  const [nodes, setNodes] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [updating, setUpdating] = React.useState(false);
  const [selectedNodes, setSelectedNodes] = React.useState<string[]>([]);

  const fetchNodes = async (force = false) => {
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8001/api/comfy/nodes${force ? '?force=true' : ''}`);
      const data = await res.json();
      setNodes(data.nodes || []);
    } catch (e) {
      console.error('Failed to fetch nodes:', e);
    }
    setLoading(false);
  };

  React.useEffect(() => {
    fetchNodes(false);
  }, []);

  const handleUpdate = async () => {
    setUpdating(true);
    try {
      const res = await fetch('http://127.0.0.1:8001/api/comfy/nodes/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes: selectedNodes })
      });
      const data = await res.json();
      if (data.success) {
        showToast('Update successful! Sending reboot signal to ComfyUI...', 'success');
        await handleReboot();
        fetchNodes(true);
      }
    } catch (e) {
      console.error('Update failed:', e);
    }
    setUpdating(false);
  };

  const toggleNode = (name: string) => {
    setSelectedNodes(prev => 
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  };

  const selectOutdated = () => {
    const outdated = nodes.filter(n => n.update_available).map(n => n.name);
    setSelectedNodes(outdated);
  };

  return (
    <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl h-[600px] flex flex-col">
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 flex items-center justify-center text-emerald-400"><ShieldCheck className="w-5 h-5" /></div>
          <div>
            <h3 className="font-bold text-white">Node Health</h3>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">Manage ComfyUI Custom Nodes</p>
          </div>
        </div>
        <div className="flex gap-2">
            <button 
                onClick={() => fetchNodes(true)}
                disabled={loading || updating}
                className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 transition-all border border-white/5"
            >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button 
                onClick={handleUpdate}
                disabled={loading || updating || (selectedNodes.length === 0)}
                className="bg-emerald-500 text-black px-4 py-2 rounded-xl font-black text-xs hover:bg-emerald-400 transition-all shadow-xl shadow-emerald-500/20 flex items-center gap-2 disabled:opacity-50 disabled:grayscale"
            >
                <Zap className="w-3.5 h-3.5 fill-current" /> {updating ? 'Updating...' : 'Update Selected'}
            </button>
        </div>
      </div>

      <div className="space-y-2 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
        {loading && nodes.length === 0 ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-4 opacity-50 h-full">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Scanning Workspace...</span>
            </div>
        ) : nodes.length === 0 ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-4 opacity-50">
                <AlertCircle className="w-8 h-8 text-slate-700" />
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">No nodes found in workspace</span>
            </div>
        ) : (() => {
            const updateRequired = nodes.filter(n => n.update_available);
            const upToDate = nodes.filter(n => !n.update_available);

            return (
                <div className="space-y-4">
                    {/* Maintenance Section */}
                    {updateRequired.length > 0 && (
                        <div className="space-y-2">
                            <div className="flex items-center justify-between px-1">
                                <div className="flex items-center gap-2">
                                    <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                                    <span className="text-[11px] font-bold text-amber-500 uppercase tracking-widest">Maintenance Required</span>
                                </div>
                                <span className="text-[10px] text-amber-500/50 font-medium">{updateRequired.length} pending</span>
                            </div>
                            <div className="space-y-2">
                                {updateRequired.map((node, idx) => (
                                    <NodeItem 
                                        key={`update-${node.name}-${idx}`}
                                        node={node}
                                        isSelected={selectedNodes.includes(node.name)}
                                        onToggle={() => toggleNode(node.name)}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* System Health Section */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between px-1">
                            <div className="flex items-center gap-2">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">System Health</span>
                            </div>
                            <span className="text-[10px] text-slate-500/50 font-medium">{upToDate.length} verified</span>
                        </div>
                        <div className="space-y-2">
                            {upToDate.length === 0 && updateRequired.length === 0 ? (
                                <div className="p-8 rounded-3xl border border-white/5 bg-white/2 flex flex-col items-center justify-center gap-3">
                                    <Activity className="w-8 h-8 text-slate-700 animate-pulse" />
                                    <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">No nodes found</span>
                                </div>
                            ) : (
                                upToDate.map((node, idx) => (
                                    <NodeItem 
                                        key={`stable-${node.name}-${idx}`}
                                        node={node}
                                        isSelected={selectedNodes.includes(node.name)}
                                        onToggle={() => toggleNode(node.name)}
                                    />
                                ))
                            )}
                        </div>
                    </div>
                </div>
            );
        })()}
      </div>
      
      {!loading && nodes.some(n => n.update_available) && (
          <button 
            onClick={(e) => { e.stopPropagation(); selectOutdated(); }}
            className="w-full py-3 rounded-2xl bg-amber-500/5 border border-amber-500/20 text-amber-500 text-[10px] font-black uppercase tracking-widest hover:bg-amber-500/10 transition-all"
          >
              Quick Select Outdated Nodes
          </button>
      )}
    </div>
  );
}


function SnapshotManager() {
  const { handleReboot, showToast } = useDashboard();
  const [snapshots, setSnapshots] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  const fetchSnapshots = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8001/api/comfy/snapshots');
      const data = await res.json();
      setSnapshots(data.snapshots || []);
    } catch (e) {
      console.error('Failed to fetch snapshots:', e);
    }
    setLoading(false);
  };

  React.useEffect(() => {
    fetchSnapshots();
  }, []);

  const handleRestore = async (id: string) => {
    if (!confirm(`Are you sure you want to restore the environment to "${id}"? Current changes will be overwritten.`)) return;
    
    try {
      const res = await fetch('http://127.0.0.1:8001/api/comfy/snapshots/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (data.success) {
        showToast('Restore initiated! Sending reboot signal...', 'success');
        await handleReboot();
      }
    } catch (e) {
      console.error('Restore failed:', e);
    }
  };

  const handleCreateSnapshot = async () => {
    const name = prompt('Enter a name for this snapshot (e.g. before_flux_update):');
    if (!name) return;
    
    try {
      await fetch('http://127.0.0.1:8001/api/comfy/snapshots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      fetchSnapshots();
    } catch (e) {
      console.error('Snapshot creation failed:', e);
    }
  };

  return (
    <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl h-[600px] flex flex-col">
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center text-amber-400"><History className="w-5 h-5" /></div>
          <div>
            <h3 className="font-bold text-white">Time Machine</h3>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">Environment Backups</p>
          </div>
        </div>
        <div className="flex gap-2">
            <button 
                onClick={fetchSnapshots}
                className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 transition-all border border-white/5"
            >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button 
                onClick={handleCreateSnapshot}
                className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 transition-all border border-white/5"
            >
                <Save className="w-4 h-4" />
            </button>
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-black/40 border border-white/5 space-y-2 shrink-0">
          <p className="text-[10px] text-slate-400 leading-relaxed font-medium">
              <span className="text-amber-500 font-black mr-1">INFO:</span>
              Snapshots are stored as JSON files in your ComfyUI workspace under <code className="bg-white/5 px-1 rounded text-amber-300">user/__manager/snapshots/</code>. 
              They are automatically created before any node update.
          </p>
      </div>

      <div className="space-y-3 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar">
        {loading && snapshots.length === 0 ? (
             <div className="py-20 flex flex-col items-center justify-center space-y-4 opacity-50 h-full">
                <RefreshCw className="w-8 h-8 animate-spin text-amber-500" />
            </div>
        ) : snapshots.length === 0 ? (
            <div className="py-10 text-center space-y-2 opacity-30">
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">No Backups Yet</p>
                <p className="text-[9px] text-slate-600 italic">Snapshots created during updates will appear here.</p>
            </div>
        ) : (
            snapshots.slice().reverse().map((snap) => (
                <SnapshotItem key={snap.id} snap={snap} onRestore={handleRestore} />
            ))
        )}
      </div>
    </div>
  );
}
function SnapshotItem({ snap, onRestore }: { snap: any, onRestore: (id: string) => void }) {
  const [expanded, setExpanded] = React.useState(false);
  const [details, setDetails] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(false);

  const fetchDetails = async () => {
    if (details) return;
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8001/api/comfy/snapshots/${snap.id}`);
      const data = await res.json();
      setDetails(data);
    } catch (e) {
      console.error('Failed to fetch snapshot details:', e);
    }
    setLoading(false);
  };

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    if (next) fetchDetails();
  };

  return (
    <div className={`group flex flex-col bg-white/5 border border-white/5 rounded-2xl transition-all ${expanded ? 'border-amber-500/30 bg-white/[0.07]' : 'hover:border-amber-500/30'}`}>
        <div className="flex items-center justify-between p-4 cursor-pointer" onClick={toggle}>
            <div className="flex items-center gap-3">
                <div className={`transition-transform duration-300 ${expanded ? 'rotate-90' : ''}`}>
                    <CheckCircle2 className={`w-3.5 h-3.5 ${expanded ? 'text-amber-400' : 'text-slate-600'}`} />
                </div>
                <div className="flex flex-col">
                    <span className="text-xs font-bold text-white truncate max-w-[140px]">{snap.name}</span>
                    <span className="text-[9px] text-slate-500 font-mono">ID: {snap.id.split('_').pop()?.replace('.json', '')}</span>
                </div>
            </div>
            <div className="flex items-center gap-2">
                <button 
                    onClick={(e) => { e.stopPropagation(); onRestore(snap.id); }}
                    className="opacity-0 group-hover:opacity-100 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 p-2 rounded-xl text-[10px] font-black uppercase transition-all flex items-center gap-2"
                >
                    <RefreshCw className="w-3 h-3" /> Restore
                </button>
            </div>
        </div>
        
        {expanded && (
            <div className="px-4 pb-4 pt-2 border-t border-white/5 animate-in slide-in-from-top-2 duration-300">
                {loading ? (
                    <div className="py-4 flex justify-center"><RefreshCw className="w-4 h-4 animate-spin text-amber-500/50" /></div>
                ) : details ? (
                    <div className="space-y-2">
                        <div className="flex items-center justify-between text-[9px] text-slate-500 uppercase font-black tracking-widest mb-2 border-b border-white/5 pb-1">
                            <span>Component</span>
                            <span>Version</span>
                        </div>
                        <div className="space-y-1.5 max-h-[200px] overflow-y-auto custom-scrollbar pr-1">
                            {/* ComfyUI core version if available */}
                            {details.comfyui && (
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-bold text-indigo-300">ComfyUI Core</span>
                                    <span className="text-[10px] text-slate-400 font-mono">{details.comfyui.version || 'unknown'}</span>
                                </div>
                            )}
                            {/* Custom nodes list */}
                            {Object.entries(details.custom_nodes || {}).map(([name, info]: [string, any], idx) => (
                                <div key={`${name}-${idx}`} className="flex items-center justify-between group/item">
                                    <span className="text-[10px] text-white/70 group-hover/item:text-white transition-colors truncate max-w-[150px]">{name}</span>
                                    <span className="text-[10px] text-slate-500 font-mono">{info.hash?.substring(0, 8) || info.version?.substring(0, 8) || '...'}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                ) : (
                    <p className="text-[9px] text-slate-600 italic">Could not load snapshot details.</p>
                )}
            </div>
        )}
    </div>
  );
}

function BotStatus() {
  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    const check = () => {
      fetch('http://127.0.0.1:8001/health')
        .then(res => res.json())
        .then(data => setConnected(data.bot_connected))
        .catch(() => setConnected(false));
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${connected ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'}`}>
      {connected ? 'Ready' : 'Offline'}
    </span>
  );
}

function ComfyStatusIndicator() {
  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    const check = () => {
      fetch('http://127.0.0.1:8001/health')
        .then(res => res.json())
        .then(data => setConnected(data.comfy_connected))
        .catch(() => setConnected(false));
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${connected ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'}`}>
      {connected ? 'Ready' : 'Offline'}
    </span>
  );
}

function GuildCard({ id, onRemove }: { id: string, onRemove: (id: string) => void }) {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch(`http://127.0.0.1:8001/api/discord/guild/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        setData(null);
        setLoading(false);
      });
  }, [id]);

  return (
    <div className="group flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-2xl hover:border-indigo-500/30 transition-all">
      <div className="flex items-center gap-3">
        {data?.icon ? (
          <img src={data.icon} className="w-8 h-8 rounded-lg shadow-lg" alt="" />
        ) : (
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 font-black text-[10px]">
            {loading ? '...' : (data?.name?.charAt(0) || '?')}
          </div>
        )}
        <div className="flex flex-col">
          <span className="text-xs font-bold text-white leading-none mb-1">{loading ? 'Loading...' : (data?.name || 'Unknown Server')}</span>
          <span className="text-[9px] text-slate-500 font-mono tracking-tight">{id}</span>
        </div>
      </div>
      <button onClick={() => onRemove(id)} className="p-2 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-500 transition-all">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function ChannelCard({ id, onRemove }: { id: string, onRemove: (id: string) => void }) {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch(`http://127.0.0.1:8001/api/discord/channel/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        setData(null);
        setLoading(false);
      });
  }, [id]);

  return (
    <div className="group flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-2xl hover:border-fuchsia-500/30 transition-all">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-fuchsia-500/10 flex items-center justify-center text-fuchsia-400 font-black text-[10px]">
          #
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-bold text-white leading-none mb-1">{loading ? 'Loading...' : (data?.name || 'Unknown Channel')}</span>
          <span className="text-[9px] text-slate-500 font-mono tracking-tight">{data?.guild_name || '...'} · {id}</span>
        </div>
      </div>
      <button onClick={() => onRemove(id)} className="p-2 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-500 transition-all">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function SetupComfyUI({ managerType, setManagerType }: {
  managerType: '--enable-manager-legacy-ui' | '--enable-manager';
  setManagerType: React.Dispatch<React.SetStateAction<'--enable-manager-legacy-ui' | '--enable-manager'>>;
}) {
  const [status, setStatus] = React.useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [steps, setSteps] = React.useState<{ step: string; success: boolean; output: string }[]>([]);

  const stepLabels: Record<string, string> = {
    clone_manager:   'Clone ComfyUI Manager',
    comfyui_manager: 'ComfyUI Manager Requirements',
    sage_attention:  'SageAttention 2.2.0',
    triton:          'Triton',
    extra_packages:  'Extra Packages (numba, gguf, cv2)',
    patch_bat:       'Patch run_nvidia_gpu.bat',
  };

  const handleSetup = async () => {
    setStatus('running');
    setSteps([]);
    try {
      const res = await fetch('http://127.0.0.1:8001/api/comfy/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manager_type: managerType })
      });
      const data = await res.json();
      setSteps(data.steps || []);
      setStatus(data.success ? 'done' : 'error');
    } catch (e) {
      setSteps([{ step: 'network', success: false, output: String(e) }]);
      setStatus('error');
    }
  };

  return (
    <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 shadow-2xl space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-violet-500/20 flex items-center justify-center text-violet-400">
            <PackagePlus className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-white">ComfyUI Setup</h3>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">Install Manager &amp; SageAttention</p>
          </div>
        </div>

        <button
          onClick={handleSetup}
          disabled={status === 'running'}
          className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:grayscale text-white px-6 py-2.5 rounded-xl font-black text-sm transition-all shadow-xl shadow-violet-500/20 active:scale-95 shrink-0"
        >
          {status === 'running'
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <PackagePlus className="w-4 h-4" />
          }
          {status === 'running' ? 'Installing…' : 'Setup ComfyUI'}
        </button>
      </div>

      {/* Manager Type Selector */}
      {status === 'idle' && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 bg-black/40 border border-white/5 p-4 rounded-2xl animate-in fade-in duration-300">
          <div className="flex-1">
            <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest block mb-1">ComfyUI Manager Flag</span>
            <p className="text-[11px] text-slate-400">Choose how ComfyUI loads the manager UI at startup.</p>
          </div>
          <div className="flex bg-[#141418] rounded-xl p-1 border border-white/5 shrink-0">
            <button
              type="button"
              onClick={() => setManagerType('--enable-manager-legacy-ui')}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${managerType === '--enable-manager-legacy-ui' ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/20' : 'text-slate-500 hover:text-slate-300'}`}
            >
              Legacy UI
            </button>
            <button
              type="button"
              onClick={() => setManagerType('--enable-manager')}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${managerType === '--enable-manager' ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/20' : 'text-slate-500 hover:text-slate-300'}`}
            >
              Node 2.0 UI (Recommended)
            </button>
          </div>
        </div>
      )}

      {/* Info note */}
      {status === 'idle' && (
        <div className="p-4 rounded-2xl bg-violet-500/5 border border-violet-500/20 text-[11px] text-slate-400 leading-relaxed animate-in fade-in duration-300">
          <span className="text-violet-400 font-black mr-1">This will:</span>
          Git clone <span className="text-white font-semibold">ComfyUI Manager</span> into your <code className="bg-white/5 px-1 rounded text-violet-300">custom_nodes</code> folder if missing,
          install its requirements via pip, install <span className="text-white font-semibold">SageAttention 2.2.0</span> &amp; <span className="text-white font-semibold">Triton</span>,
          install extra dependencies (<span className="text-violet-300 font-semibold">numba, gguf, opencv-python</span>), and patch
          <code className="bg-white/5 px-1 rounded text-violet-300 mx-1">run_nvidia_gpu.bat</code>
          with <code className="bg-white/5 px-1 rounded text-violet-300">--use-sage-attention {managerType}</code>.
        </div>
      )}

      {/* Step results */}
      {steps.length > 0 && (
        <div className="space-y-3">
          {steps.map((s) => (
            <div
              key={s.step}
              className={`flex items-start gap-3 p-3 rounded-2xl border transition-all ${
                s.success
                  ? 'bg-emerald-500/5 border-emerald-500/20'
                  : 'bg-rose-500/5 border-rose-500/20'
              }`}
            >
              <div className={`mt-0.5 shrink-0 ${s.success ? 'text-emerald-400' : 'text-rose-400'}`}>
                {s.success
                  ? <CheckCircle2 className="w-4 h-4" />
                  : <AlertCircle className="w-4 h-4" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-bold ${s.success ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {stepLabels[s.step] ?? s.step}
                </p>
                {s.output && (
                  <pre className="mt-1 text-[9px] text-slate-500 font-mono whitespace-pre-wrap break-all leading-relaxed max-h-24 overflow-y-auto custom-scrollbar">
                    {s.output.trim()}
                  </pre>
                )}
              </div>
            </div>
          ))}

          {status === 'done' && (
            <p className="text-center text-[11px] font-black text-emerald-400 uppercase tracking-widest animate-in fade-in duration-500">
              ✓ Setup complete – restart ComfyUI to apply changes.
            </p>
          )}
          {status === 'error' && (
            <p className="text-center text-[11px] font-black text-rose-400 uppercase tracking-widest animate-in fade-in duration-500">
              ✗ One or more steps failed. Check the output above.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
