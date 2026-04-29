"use client";

import React from 'react';
import { Type, CheckCircle2, ChevronLeft, ChevronRight, Upload, Trash2 } from 'lucide-react';
import { useDashboard } from './DashboardProvider';
import { VisualWorkflowMap } from './VisualWorkflowMap';
import { ListView } from './ListView';

export function ArchitectView() {
  const { workflows, selectedWorkflow, loadWorkflow, viewMode, setViewMode, customCommandName, setCustomCommandName, displayName, setDisplayName, selections, moveInput, importWorkflow, deleteWorkflow } = useDashboard();
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
        alert('Invalid JSON file');
      }
    };
    reader.readAsText(file);
    // Clear the input so the same file can be imported again if needed
    e.target.value = '';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[250px_1fr] gap-8 h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="space-y-4">
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
        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-200px)] pr-2">
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
      
      <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 shadow-2xl overflow-hidden relative flex flex-col">
        {selectedWorkflow ? (
          <>
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/20">
              <div className="flex items-center gap-6">
                <div className="flex bg-[#141418] rounded-xl p-1 border border-white/5">
                  <button onClick={() => setViewMode('list')} className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'list' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:text-slate-300'}`}>List View</button>
                  <button onClick={() => setViewMode('visual')} className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'visual' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:text-slate-300'}`}>Visual Architect</button>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter ml-1">Discord Workflow list name</span>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 rounded-lg border border-indigo-500/20 shadow-inner">
                    <Type className="w-3 h-3 text-indigo-400" />
                    <input 
                      value={displayName} 
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Display Name"
                      className="bg-transparent border-none text-xs font-bold text-indigo-400 outline-none w-36 placeholder-indigo-400/30"
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter ml-1">Discord Command</span>
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-500/10 rounded-lg border border-white/5 shadow-inner">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">/</span>
                    <input 
                      value={customCommandName} 
                      onChange={(e) => setCustomCommandName(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ''))}
                      placeholder="Command"
                      className="bg-transparent border-none text-xs font-bold text-slate-400 outline-none w-28 placeholder-slate-600"
                    />
                  </div>
                </div>
              </div>
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
          <div className="flex-1 flex flex-col items-center justify-center p-20 opacity-30 h-full">
            <h3 className="text-lg font-bold text-slate-400">Architect Canvas</h3>
            <p className="text-sm text-slate-600">Select a workflow from the sidebar to begin orchestration</p>
          </div>
        )}
      </div>
    </div>
  );
}
