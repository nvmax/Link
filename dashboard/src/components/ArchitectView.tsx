"use client";

import React from 'react';
import { Type, CheckCircle2, ChevronLeft, ChevronRight, Upload, Trash2, Sparkles, Video, Image as ImageIcon, Eye, Zap, HelpCircle } from 'lucide-react';
import { useDashboard } from './DashboardProvider';
import { VisualWorkflowMap } from './VisualWorkflowMap';
import { ListView } from './ListView';

export function ArchitectView() {
  const { 
    workflows, selectedWorkflow, loadWorkflow, isLoadingWorkflow, viewMode, setViewMode, 
    customCommandName, setCustomCommandName, displayName, setDisplayName, 
    selections, moveInput, importWorkflow, deleteWorkflow,
    aiPrompt, setAiPrompt, systemPrompts, showToast
  } = useDashboard();
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string);
        importWorkflow(file.name, json);
      } catch (err) {
        showToast('Invalid JSON file', 'error');
      }
    };
    reader.readAsText(file);
    // Clear the input so the same file can be imported again if needed
    e.target.value = '';
  };

  return (
    <div className="flex flex-col lg:flex-row gap-8 h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="w-full lg:w-[250px] space-y-4 shrink-0">
        <div className="flex flex-col gap-4 mb-4">
          <h3 className="text-xs text-slate-500 uppercase tracking-widest font-bold">Workflows</h3>
          <div className="flex gap-2">
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="flex-1 flex items-center justify-center gap-2 p-4 bg-indigo-500 text-white rounded-2xl hover:bg-indigo-400 transition-all shadow-lg shadow-indigo-500/20 font-black text-[10px] uppercase tracking-widest"
              title="Import Workflow (API)"
            >
              <Upload className="w-4 h-4" />
              Import Workflow (API)
            </button>
            {selectedWorkflow && (
              <button 
                onClick={() => deleteWorkflow(selectedWorkflow.name)}
                className="p-4 bg-rose-500/10 text-rose-500 rounded-2xl hover:bg-rose-500 hover:text-white transition-all border border-rose-500/20 shadow-lg shadow-rose-500/5 group"
                title="Delete Workflow"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileImport} 
            className="hidden" 
            accept=".json"
          />
        </div>
        <div className="space-y-2 overflow-y-auto max-h-[200px] lg:max-h-[calc(100vh-280px)] pr-2">
          {workflows.map((wf) => (
            <button 
              key={wf.name}
              onClick={() => loadWorkflow(wf)}
              className={`w-full flex items-center justify-between p-4 rounded-2xl transition-all border ${selectedWorkflow?.name === wf.name ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400 shadow-xl shadow-indigo-500/5' : 'bg-[#141418] border-white/5 text-slate-400 hover:bg-white/5'}`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${selectedWorkflow?.name === wf.name ? 'bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]' : 'bg-slate-600'}`} />
                <span className="font-bold text-sm truncate max-w-[180px]">{wf.name}</span>
              </div>
              <span className="text-[10px] opacity-50 font-mono">.json</span>
            </button>
          ))}
        </div>
      </div>
      
      <div className="flex-1 bg-[#0d0d0f] rounded-3xl border border-white/5 shadow-2xl overflow-hidden relative flex flex-col min-h-[500px]">
        {isLoadingWorkflow ? (
          <div className="absolute inset-0 bg-[#0a0a0c]/80 backdrop-blur-md z-45 flex flex-col items-center justify-center gap-6 animate-in fade-in duration-300">
            <div className="relative flex items-center justify-center">
              {/* Core glowing ring */}
              <div className="w-16 h-16 rounded-full border-2 border-indigo-500/10 border-t-indigo-500 animate-spin shadow-[0_0_15px_rgba(99,102,241,0.2)]" />
              {/* Outer orbit secondary ring */}
              <div className="absolute w-24 h-24 rounded-full border border-dashed border-indigo-500/20 animate-[spin_10s_linear_infinite]" />
              {/* Floating tech nodes */}
              <div className="absolute w-2 h-2 bg-indigo-400 rounded-full animate-ping" />
            </div>
            <div className="flex flex-col items-center gap-1.5 text-center">
              <h4 className="text-sm font-black text-white uppercase tracking-widest animate-pulse">Analyzing Workflow</h4>
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-tight max-w-[220px]">Running ComfyUI model validation & schema extraction...</p>
            </div>
          </div>
        ) : null}

        {selectedWorkflow ? (
          <>
            <div className="p-4 sm:p-6 border-b border-white/5 flex flex-col md:flex-row items-center justify-between bg-black/20 gap-4">
              <div className="flex items-center gap-6 w-full md:w-auto">
                <div className="flex bg-[#141418] rounded-xl p-1 border border-white/5 w-full md:w-auto">
                  <button onClick={() => setViewMode('list')} className={`flex-1 md:flex-none px-4 py-1.5 rounded-lg text-[10px] sm:text-xs font-bold transition-all ${viewMode === 'list' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:text-slate-300'}`}>List View</button>
                  <button onClick={() => setViewMode('visual')} className={`flex-1 md:flex-none px-4 py-1.5 rounded-lg text-[10px] sm:text-xs font-bold transition-all ${viewMode === 'visual' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:text-slate-300'}`}>Visual Architect</button>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-4 w-full md:w-auto justify-end">
                <div className="flex flex-col gap-1 flex-1 sm:flex-none">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter ml-1">Discord Workflow list name</span>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 rounded-lg border border-indigo-500/20 shadow-inner">
                    <Type className="w-3 h-3 text-indigo-400" />
                    <input 
                      value={displayName || ''} 
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Display Name"
                      className="bg-transparent border-none text-xs font-bold text-indigo-400 outline-none w-36 placeholder-indigo-400/30"
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-1 flex-1 sm:flex-none">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter ml-1">Discord Command</span>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-500/10 rounded-lg border border-white/5 shadow-inner">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">/</span>
                    <input 
                      value={customCommandName || ''} 
                      onChange={(e) => setCustomCommandName(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ''))}
                      placeholder="Command"
                      className="bg-transparent border-none text-xs font-bold text-slate-400 outline-none w-full sm:w-28 placeholder-slate-600"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* AI Enhancement Settings */}
            <div className="px-6 py-4 border-b border-indigo-500/10 bg-indigo-500/[0.02] flex items-center justify-between gap-6 overflow-x-auto scrollbar-hide">
              <div className="flex items-center gap-6 shrink-0">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${aiPrompt.enabled ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'bg-slate-800 text-slate-500 opacity-50'}`}>
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-black text-white uppercase tracking-tight">AI Enhancement</span>
                      <button 
                        onClick={() => setAiPrompt({ ...aiPrompt, enabled: !aiPrompt.enabled, auto: aiPrompt.auto !== undefined ? aiPrompt.auto : true })}
                        className={`w-8 h-4 rounded-full relative transition-all ${aiPrompt.enabled ? 'bg-indigo-500' : 'bg-slate-700'}`}
                      >
                        <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${aiPrompt.enabled ? 'left-4.5' : 'left-0.5'}`} />
                      </button>
                    </div>
                    <p className="text-[10px] text-slate-500 font-medium">Use LLM to rewrite user prompts before execution.</p>
                  </div>
                </div>
              </div>

              {aiPrompt.enabled && (
                <div className="flex items-center gap-6 animate-in fade-in slide-in-from-left-2 duration-300">
                  <div className="h-8 w-px bg-white/5" />
                  
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-tighter ml-1">Modality</span>
                    <div className="flex bg-black/40 rounded-lg p-0.5 border border-white/5">
                      <button 
                        onClick={() => setAiPrompt({ ...aiPrompt, category: 'image' })}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${aiPrompt.category === 'image' ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-500 hover:text-slate-400'}`}
                      >
                        <ImageIcon className="w-3 h-3 inline mr-1" /> Image
                      </button>
                      <button 
                        onClick={() => setAiPrompt({ ...aiPrompt, category: 'video' })}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${aiPrompt.category === 'video' ? 'bg-fuchsia-500/20 text-fuchsia-400' : 'text-slate-500 hover:text-slate-400'}`}
                      >
                        <Video className="w-3 h-3 inline mr-1" /> Video
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-tighter ml-1">Mode</span>
                    <div className="flex bg-black/40 rounded-lg p-0.5 border border-white/5">
                      <button 
                        onClick={() => setAiPrompt({ ...aiPrompt, auto: true })}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${aiPrompt.auto !== false ? 'bg-emerald-500/20 text-emerald-400' : 'text-slate-500 hover:text-slate-400'}`}
                        title="Full Auto: Automatically enhances prompt using the specified system prompt"
                      >
                        <Zap className="w-3 h-3 inline mr-1" /> Full Auto
                      </button>
                      <button 
                        onClick={() => setAiPrompt({ ...aiPrompt, auto: false })}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${aiPrompt.auto === false ? 'bg-sky-500/20 text-sky-400' : 'text-slate-500 hover:text-slate-400'}`}
                        title="Ask User: Discord bot asks the user if they want to enhance their prompt before running"
                      >
                        <HelpCircle className="w-3 h-3 inline mr-1" /> Ask User
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-tighter ml-1">Context Mode</span>
                    <div className="flex bg-black/40 rounded-lg p-0.5 border border-white/5">
                      <button 
                        onClick={() => setAiPrompt({ ...aiPrompt, include_image: false })}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${!aiPrompt.include_image ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-500 hover:text-slate-400'}`}
                        title="Enhance prompt from text input only"
                      >
                        <Type className="w-3 h-3 inline mr-1" /> Text Only
                      </button>
                      <button 
                        onClick={() => setAiPrompt({ ...aiPrompt, include_image: true })}
                        className={`px-3 py-1 rounded-md text-[10px] font-bold transition-all ${aiPrompt.include_image ? 'bg-amber-500/20 text-amber-400' : 'text-slate-500 hover:text-slate-400'}`}
                        title="Send uploaded keyframe/image alongside prompt to Vision LLM"
                      >
                        <Eye className="w-3 h-3 inline mr-1" /> + Image (Vision)
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1 min-w-[150px]">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-tighter ml-1">System Prompt</span>
                    <select 
                      value={aiPrompt.prompt_id}
                      onChange={(e) => setAiPrompt({ ...aiPrompt, prompt_id: e.target.value })}
                      className="bg-black/40 border border-white/5 rounded-lg px-3 py-1.5 text-[10px] font-bold text-indigo-300 outline-none focus:border-indigo-500/30 transition-all cursor-pointer appearance-none"
                    >
                      <option value="">Select Prompt...</option>
                      {systemPrompts.filter(p => p.category === aiPrompt.category).map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="flex flex-col gap-1 min-w-[150px]">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-tighter ml-1">Target Prompt Input</span>
                    <select 
                      value={aiPrompt.target_input}
                      onChange={(e) => setAiPrompt({ ...aiPrompt, target_input: e.target.value })}
                      className="bg-black/40 border border-white/5 rounded-lg px-3 py-1.5 text-[10px] font-bold text-emerald-400 outline-none focus:border-emerald-500/30 transition-all cursor-pointer appearance-none"
                    >
                      <option value="">Select Input...</option>
                      {selections.filter((s: any) => s.type === 'text' || s.type === 'string').map((s: any) => (
                        <option key={s.id} value={s.id}>{s.label}</option>
                      ))}
                    </select>
                  </div>

                  {aiPrompt.include_image && (
                    <div className="flex flex-col gap-1 min-w-[150px] animate-in fade-in slide-in-from-left-2 duration-300">
                      <span className="text-[10px] font-black text-amber-400 uppercase tracking-tighter ml-1 flex items-center gap-1">
                        <ImageIcon className="w-2.5 h-2.5" /> Target Image
                      </span>
                      <select 
                        value={aiPrompt.target_image || ''}
                        onChange={(e) => setAiPrompt({ ...aiPrompt, target_image: e.target.value })}
                        className="bg-black/40 border border-amber-500/30 rounded-lg px-3 py-1.5 text-[10px] font-bold text-amber-400 outline-none focus:border-amber-500/50 transition-all cursor-pointer appearance-none"
                      >
                        <option value="">Auto-detect from upload...</option>
                        {(selections.filter((s: any) => ['image_upload', 'inpaint', 'image', 'file'].includes(s.type) || s.field?.toLowerCase().includes('image') || s.id?.toLowerCase().includes('image')).length > 0
                          ? selections.filter((s: any) => ['image_upload', 'inpaint', 'image', 'file'].includes(s.type) || s.field?.toLowerCase().includes('image') || s.id?.toLowerCase().includes('image'))
                          : selections
                        ).map((s: any) => (
                          <option key={s.id || s.field} value={s.id || s.field}>{s.label || s.field}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {selections.length > 0 && (
              <div className="p-4 border-b border-white/5 bg-black/40 flex items-center gap-2 overflow-x-auto whitespace-nowrap scrollbar-hide">
                <span className="text-[10px] font-bold text-slate-500 uppercase mr-2 tracking-widest">Order:</span>
                {selections.map((sel: any, idx: number) => (
                  <div key={`${sel.nodeId}-${sel.field}`} className="flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl px-3 py-1.5 shrink-0 hover:border-indigo-500/40 transition-colors">
                    <span className="text-xs font-bold text-indigo-400">{sel.label}</span>
                    <div className="flex items-center gap-1 border-l border-white/10 pl-2 ml-1">
                      <button onClick={() => moveInput(idx, 'up')} className="text-slate-500 hover:text-white transition-colors" disabled={idx === 0}><ChevronLeft className="w-3.5 h-3.5" /></button>
                      <button onClick={() => moveInput(idx, 'down')} className="text-slate-500 hover:text-white transition-colors" disabled={idx === selections.length - 1}><ChevronRight className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex-1 overflow-hidden relative">
              {viewMode === 'list' ? <ListView /> : <VisualWorkflowMap />}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-20 opacity-30 h-full animate-in fade-in duration-300">
            <h3 className="text-lg font-bold text-slate-400">Architect Canvas</h3>
            <p className="text-sm text-slate-600">Select a workflow from the sidebar to begin orchestration</p>
          </div>
        )}
      </div>
    </div>
  );
}
