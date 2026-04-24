"use client";

import React from 'react';
import { Layers, ChevronRight, CheckCircle2, ArrowUp, ArrowDown, Trash2, Plus } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function LoraStudio() {
  const { 
    loraFiles, 
    editingLoraFile, 
    loadLoraFile, 
    saveLoraFile, 
    updateLoraField, 
    moveLora, 
    deleteLora, 
    addLora 
  } = useDashboard();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-8 h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="space-y-4">
        <h3 className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-4">LoRA Lists</h3>
        <div className="space-y-2">
          {loraFiles.map((file) => (
            <button 
              key={file.name}
              onClick={() => loadLoraFile(file)}
              className={`w-full flex items-center justify-between p-4 rounded-2xl transition-all border ${editingLoraFile?.name === file.name ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 shadow-xl shadow-amber-500/5' : 'bg-[#141418] border-white/5 text-slate-400 hover:bg-white/5'}`}
            >
              <div className="flex items-center gap-3">
                <Layers className="w-4 h-4" />
                <span className="text-sm font-medium">{file.name}</span>
              </div>
              <ChevronRight className={`w-4 h-4 transition-transform ${editingLoraFile?.name === file.name ? 'rotate-90' : ''}`} />
            </button>
          ))}
          {loraFiles.length === 0 && (
            <div className="p-4 text-xs text-slate-500 italic text-center">
              No LoRA files found.
            </div>
          )}
        </div>
      </div>

      <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 overflow-hidden flex flex-col relative shadow-2xl">
          {editingLoraFile ? (
            <div className="flex-1 flex flex-col h-full overflow-hidden">
              <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/20 backdrop-blur-xl shrink-0">
                <div className="flex flex-col">
                  <span className="text-xs text-slate-500 font-bold uppercase tracking-widest">Managing List</span>
                  <h3 className="text-lg font-black text-white">{editingLoraFile.name}</h3>
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={saveLoraFile} className="flex items-center gap-2 bg-amber-500 text-black px-6 py-2.5 rounded-xl font-black text-sm hover:bg-amber-400 transition-all shadow-xl shadow-amber-500/20 active:scale-95">
                    <CheckCircle2 className="w-4 h-4" />
                    Save Changes
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-8">
                  <div className="grid grid-cols-1 gap-4 pb-20">
                    {editingLoraFile.content?.map((lora: any, idx: number) => (
                      <div key={idx} className="group p-6 bg-white/5 rounded-3xl border border-white/5 hover:border-amber-500/30 transition-all shadow-lg hover:shadow-amber-500/5">
                          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-6 items-center">
                            <div className="space-y-4">
                              <div className="grid gap-2">
                                <label className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">LoRA Name</label>
                                <input value={lora.name} onChange={(e) => updateLoraField(idx, 'name', e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm text-white font-bold focus:border-amber-500/50 outline-none" />
                              </div>
                              <div className="grid gap-2">
                                <label className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">Model Filename</label>
                                <input value={lora.file} onChange={(e) => updateLoraField(idx, 'file', e.target.value)} className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-xs font-mono text-amber-400/80 focus:border-amber-500/50 outline-none" />
                              </div>
                            </div>
                            <div className="grid gap-2 h-full">
                              <label className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">Trigger Prompt</label>
                              <textarea 
                                value={lora.add_prompt || ''} 
                                onChange={(e) => updateLoraField(idx, 'add_prompt', e.target.value)} 
                                className="w-full h-full min-h-[100px] bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-xs text-emerald-400/90 resize-none focus:border-amber-500/50 outline-none"
                              ></textarea>
                            </div>
                            <div className="flex flex-col gap-2">
                                <button onClick={() => moveLora(idx, 'up')} className="p-3 bg-white/5 rounded-xl text-slate-500 hover:text-white hover:bg-white/10 transition-all"><ArrowUp className="w-4 h-4" /></button>
                                <button onClick={() => moveLora(idx, 'down')} className="p-3 bg-white/5 rounded-xl text-slate-500 hover:text-white hover:bg-white/10 transition-all"><ArrowDown className="w-4 h-4" /></button>
                                <button onClick={() => deleteLora(idx)} className="p-3 bg-rose-500/10 rounded-xl text-rose-500 hover:bg-rose-500 hover:text-white transition-all"><Trash2 className="w-4 h-4" /></button>
                            </div>
                          </div>
                      </div>
                    ))}
                    
                    <button onClick={addLora} className="p-8 border-2 border-dashed border-white/5 rounded-3xl text-slate-500 hover:border-amber-500/30 hover:text-amber-400 transition-all flex flex-col items-center gap-2 group">
                        <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-amber-500/20"><Plus className="w-5 h-5" /></div>
                        <span className="text-xs font-bold uppercase tracking-widest">Add New LoRA Entry</span>
                    </button>
                  </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-20 opacity-30">
              <Layers className="w-16 h-16 mb-6 text-slate-600" />
              <h3 className="text-lg font-bold text-slate-400">LoRA Management Studio</h3>
              <p className="text-sm text-slate-600">Select a list from the sidebar to manage LoRA configurations</p>
            </div>
          )}
      </div>
    </div>
  );
}
