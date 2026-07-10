"use client";

import React, { useState } from 'react';
import { 
  Sparkles, 
  Settings, 
  Plus, 
  Trash2, 
  Edit2, 
  Save, 
  Database, 
  Cpu, 
  CheckCircle2, 
  AlertCircle,
  Video,
  Image as ImageIcon,
  ChevronRight,
  Monitor,
  Zap,
  RefreshCw
} from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function AiStudio() {
  const { 
    aiConfig, 
    saveAiConfig, 
    systemPrompts, 
    saveSystemPrompts 
  } = useDashboard();

  const [activeCategory, setActiveCategory] = useState<'image' | 'video'>('image');
  const [editingPrompt, setEditingPrompt] = useState<any>(null);
  const [isAddingPrompt, setIsAddingPrompt] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean, message: string } | null>(null);

  const filteredPrompts = systemPrompts.filter(p => p.category === activeCategory);

  const handleToggleProvider = (providerId: string) => {
    const newConfig = { ...aiConfig, active_provider: providerId };
    // Update all providers active status based on the new active_provider
    Object.keys(newConfig.providers).forEach(id => {
      newConfig.providers[id].active = (id === providerId);
    });
    saveAiConfig(newConfig);
  };

  const handleUpdateProviderField = (providerId: string, field: string, value: string) => {
    const newConfig = { ...aiConfig };
    newConfig.providers[providerId][field] = value;
    saveAiConfig(newConfig);
  };

  const handleDeletePrompt = (id: string) => {
    if (confirm('Are you sure you want to delete this system prompt?')) {
      const newPrompts = systemPrompts.filter(p => p.id !== id);
      saveSystemPrompts(newPrompts);
    }
  };

  const handleSavePrompt = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    const promptData = {
      id: editingPrompt?.id || `prompt-${Date.now()}`,
      name: formData.get('name') as string,
      category: formData.get('category') as string,
      content: formData.get('content') as string,
    };

    let newPrompts;
    if (editingPrompt) {
      newPrompts = systemPrompts.map(p => p.id === editingPrompt.id ? promptData : p);
    } else {
      newPrompts = [...systemPrompts, promptData];
    }

    saveSystemPrompts(newPrompts);
    setEditingPrompt(null);
    setIsAddingPrompt(false);
  };

  const [selectedProviderId, setSelectedProviderId] = useState<string>(aiConfig.active_provider || Object.keys(aiConfig.providers || {})[0] || '');

  const currentProvider = aiConfig.providers?.[selectedProviderId];

  return (
    <div className="flex flex-col gap-8 h-full animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between bg-[#0d0d0f] p-8 rounded-3xl border border-white/5 shadow-2xl">
        <div className="flex items-center gap-6">
          <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-fuchsia-500 rounded-2xl flex items-center justify-center shadow-2xl shadow-indigo-500/20">
            <Sparkles className="text-white w-8 h-8" />
          </div>
          <div>
            <h2 className="text-3xl font-black text-white tracking-tighter">AI Studio</h2>
            <p className="text-slate-500 text-sm font-medium mt-1">Manage prompt enhancement brains and system personas.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Provider Settings */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 shadow-xl space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Cpu className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-white text-lg">AI Provider</h3>
              </div>
              {aiConfig.active_provider === selectedProviderId && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[9px] font-black text-emerald-500 uppercase tracking-tight">Active</span>
                </div>
              )}
            </div>

            <div className="space-y-4">
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-black uppercase text-slate-500 ml-1">Select Provider</label>
                <div className="relative group">
                  <select 
                    value={selectedProviderId}
                    onChange={(e) => setSelectedProviderId(e.target.value)}
                    className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-indigo-500 transition-all appearance-none cursor-pointer pr-10"
                  >
                    {aiConfig.providers && Object.keys(aiConfig.providers).map(id => (
                      <option key={id} value={id}>{id.charAt(0).toUpperCase() + id.slice(1)}</option>
                    ))}
                  </select>
                  <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none rotate-90" />
                </div>
              </div>

              {currentProvider && (
                <div className="space-y-4 pt-2 animate-in fade-in slide-in-from-top-2 duration-300">
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-black uppercase text-slate-500 ml-1">Model Name</label>
                    <input 
                      value={currentProvider.model}
                      onChange={(e) => handleUpdateProviderField(selectedProviderId, 'model', e.target.value)}
                      className="bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm text-indigo-300 outline-none focus:border-indigo-500/50 transition-all font-mono shadow-inner"
                      placeholder="e.g. gpt-4o"
                    />
                  </div>

                  {selectedProviderId !== 'openai' && selectedProviderId !== 'gemini' && selectedProviderId !== 'anthropic' && selectedProviderId !== 'grok' && (
                    <div className="flex flex-col gap-2">
                      <label className="text-[10px] font-black uppercase text-slate-500 ml-1">Base URL</label>
                      <input 
                        value={currentProvider.base_url || ''}
                        onChange={(e) => handleUpdateProviderField(selectedProviderId, 'base_url', e.target.value)}
                        className="bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm text-slate-300 outline-none focus:border-indigo-500/50 transition-all font-mono shadow-inner"
                        placeholder="http://localhost:11434/v1"
                      />
                    </div>
                  )}

                  <button 
                    onClick={() => handleToggleProvider(selectedProviderId)}
                    disabled={aiConfig.active_provider === selectedProviderId}
                    className={`w-full py-4 rounded-2xl font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${
                      aiConfig.active_provider === selectedProviderId 
                      ? 'bg-emerald-500/10 text-emerald-500 cursor-default border border-emerald-500/20' 
                      : 'bg-indigo-500 hover:bg-indigo-400 text-white shadow-lg shadow-indigo-500/20 active:scale-95'
                    }`}
                  >
                    {aiConfig.active_provider === selectedProviderId ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      <Monitor className="w-4 h-4" />
                    )}
                    {aiConfig.active_provider === selectedProviderId ? 'Primary Brain Active' : 'Set as Primary Brain'}
                  </button>

                  {aiConfig.active_provider === selectedProviderId && (
                    <button 
                      onClick={async () => {
                        setIsTesting(true);
                        setTestResult(null);
                        try {
                          const res = await fetch('http://127.0.0.1:8001/api/ai/test', { method: 'POST' });
                          const data = await res.json();
                          if (data.status === 'success') {
                            setTestResult({ success: true, message: data.response });
                          } else {
                            setTestResult({ success: false, message: data.detail || 'Test failed' });
                          }
                        } catch (e) {
                          setTestResult({ success: false, message: 'Connection error' });
                        }
                        setIsTesting(false);
                      }}
                      disabled={isTesting}
                      className="w-full py-3 rounded-2xl bg-white/5 border border-white/10 text-[10px] font-black uppercase tracking-widest hover:bg-white/10 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      {isTesting ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                      ) : (
                        <Zap className="w-3.5 h-3.5 text-indigo-400 fill-current" />
                      )}
                      {isTesting ? 'Testing Link...' : 'Test Connection'}
                    </button>
                  )}

                  {testResult && (
                    <div className={`p-3 rounded-xl border text-[10px] font-bold flex items-center gap-2 animate-in fade-in slide-in-from-top-1 ${testResult.success ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
                      {testResult.success ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                      {testResult.message}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {['openai', 'gemini', 'anthropic', 'grok'].includes(selectedProviderId) && (
            <div className="bg-amber-500/5 border border-amber-500/20 p-6 rounded-3xl space-y-3">
              <div className="flex items-center gap-2 text-amber-500">
                <AlertCircle className="w-4 h-4" />
                <span className="text-xs font-bold uppercase tracking-tight">API Key Required</span>
              </div>
              <p className="text-[11px] text-amber-500/70 font-medium leading-relaxed">
                Make sure to set your API keys in <strong>Mission Control</strong> under the Environment section. Standard keys like <code>OPENAI_API_KEY</code> are used for cloud providers.
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Prompt Library */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-8 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
              <div className="flex items-center gap-3">
                <Database className="w-6 h-6 text-fuchsia-400" />
                <h3 className="font-bold text-white text-xl">System Prompt Library</h3>
              </div>
              
              <div className="flex items-center gap-4 bg-black/40 p-1.5 rounded-2xl border border-white/5">
                <button 
                  onClick={() => setActiveCategory('image')}
                  className={`flex items-center gap-2 px-6 py-2 rounded-xl text-xs font-bold transition-all ${activeCategory === 'image' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-500 hover:text-slate-300'}`}
                >
                  <ImageIcon className="w-3.5 h-3.5" />
                  Images
                </button>
                <button 
                  onClick={() => setActiveCategory('video')}
                  className={`flex items-center gap-2 px-6 py-2 rounded-xl text-xs font-bold transition-all ${activeCategory === 'video' ? 'bg-fuchsia-500 text-white shadow-lg shadow-fuchsia-500/20' : 'text-slate-500 hover:text-slate-300'}`}
                >
                  <Video className="w-3.5 h-3.5" />
                  Videos
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredPrompts.map((prompt) => (
                <div key={prompt.id} className="group bg-[#141418] border border-white/5 rounded-2xl p-5 hover:border-indigo-500/30 transition-all flex flex-col justify-between shadow-lg">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${prompt.category === 'image' ? 'bg-indigo-500' : 'bg-fuchsia-500'}`} />
                        <h4 className="font-bold text-white text-sm">{prompt.name}</h4>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => setEditingPrompt(prompt)}
                          className="p-2 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-all"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button 
                          onClick={() => handleDeletePrompt(prompt.id)}
                          className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-500 line-clamp-3 leading-relaxed mb-4">
                      {prompt.content}
                    </p>
                  </div>
                  <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase text-slate-600 tracking-widest">{prompt.id}</span>
                    <ChevronRight className="w-4 h-4 text-slate-700" />
                  </div>
                </div>
              ))}

              <button 
                onClick={() => setIsAddingPrompt(true)}
                className="flex flex-col items-center justify-center gap-4 p-8 rounded-2xl border border-dashed border-white/10 text-slate-500 hover:border-indigo-500/50 hover:text-indigo-400 hover:bg-indigo-500/5 transition-all group"
              >
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Plus className="w-6 h-6" />
                </div>
                <span className="text-xs font-bold uppercase tracking-widest">New System Prompt</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Editor Modal */}
      {(editingPrompt || isAddingPrompt) && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-[#0d0d0f] w-full max-w-2xl rounded-3xl border border-white/10 shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/20">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-indigo-500/10 rounded-xl flex items-center justify-center text-indigo-400">
                  <Edit2 className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-bold text-white">{editingPrompt ? 'Edit System Prompt' : 'New System Prompt'}</h3>
              </div>
              <button 
                onClick={() => { setEditingPrompt(null); setIsAddingPrompt(false); }}
                className="p-2 text-slate-500 hover:text-white hover:bg-white/5 rounded-xl transition-all"
              >
                <Plus className="w-6 h-6 rotate-45" />
              </button>
            </div>

            <form onSubmit={handleSavePrompt} className="flex-1 overflow-y-auto p-8 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-black uppercase text-slate-500 ml-1">Prompt Name</label>
                  <input 
                    name="name"
                    required
                    defaultValue={editingPrompt?.name || ''}
                    placeholder="e.g. Flux Master Artist"
                    className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-indigo-500 transition-all shadow-inner"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-black uppercase text-slate-500 ml-1">Category</label>
                  <select 
                    name="category"
                    defaultValue={editingPrompt?.category || activeCategory}
                    className="bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm text-white outline-none focus:border-indigo-500 transition-all shadow-inner appearance-none cursor-pointer"
                  >
                    <option value="image">Image Prompting</option>
                    <option value="video">Video Prompting</option>
                  </select>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-black uppercase text-slate-500 ml-1">System Instructions</label>
                <textarea 
                  name="content"
                  required
                  defaultValue={editingPrompt?.content || ''}
                  placeholder="Describe the AI's persona and how it should enhance prompts..."
                  className="bg-black/40 border border-white/10 rounded-xl px-4 py-4 text-sm text-white outline-none focus:border-indigo-500 transition-all shadow-inner min-h-[300px] leading-relaxed"
                />
              </div>

              <div className="flex items-center gap-4 pt-4">
                <button 
                  type="submit"
                  className="flex-1 bg-indigo-500 hover:bg-indigo-400 text-white font-black py-4 rounded-2xl transition-all shadow-lg shadow-indigo-500/20 uppercase tracking-widest text-xs flex items-center justify-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  Save System Prompt
                </button>
                <button 
                  type="button"
                  onClick={() => { setEditingPrompt(null); setIsAddingPrompt(false); }}
                  className="px-8 py-4 text-slate-400 font-bold hover:text-white transition-all text-xs uppercase tracking-widest"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
