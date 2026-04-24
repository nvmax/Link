"use client";

import React from 'react';
import { Layout, List, Type, ArrowUp, ArrowDown, Eye } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function ModalStudio() {
  const { selections, updateSelection, moveInput, uiConfig, setUiConfig } = useDashboard();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-8 h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-8 overflow-y-auto shadow-2xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h3 className="text-2xl font-black text-white tracking-tight">Modal Studio</h3>
            <p className="text-slate-500 text-sm">Design the generation interaction flow for Discord</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-10">
          <div className="space-y-6">
              <h4 className="text-xs font-black text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                <Layout className="w-3 h-3" /> Embed Layout
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 uppercase font-bold">Title Template</label>
                  <input 
                    value={uiConfig.embed.title_template}
                    onChange={(e) => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, title_template: e.target.value } })}
                    className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-xs text-white"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 uppercase font-bold">Accent Color</label>
                  <div className="flex gap-2">
                    <input type="color" value={uiConfig.embed.color} onChange={(e) => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, color: e.target.value } })} className="w-10 h-10 rounded-lg bg-transparent border-none cursor-pointer" />
                    <input value={uiConfig.embed.color} onChange={(e) => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, color: e.target.value } })} className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 text-xs font-mono text-white" />
                  </div>
                </div>
              </div>
          </div>

          <div className="space-y-6">
              <h4 className="text-xs font-black text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                <List className="w-3 h-3" /> Input Ordering
              </h4>
              <div className="space-y-3">
                {selections.map((sel, idx) => (
                  <div key={`${sel.nodeId}-${sel.field}`} className="group p-4 bg-white/5 rounded-2xl border border-white/5 flex items-center justify-between hover:border-indigo-500/30 transition-all">
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 rounded-xl bg-black/40 flex items-center justify-center text-xs font-bold text-slate-500 group-hover:text-indigo-400 transition-colors">{idx + 1}</div>
                      <div className="flex flex-col">
                        <input 
                          value={sel.label}
                          onChange={(e) => updateSelection(idx, { label: e.target.value })}
                          className="bg-transparent border-none text-sm font-bold text-white outline-none focus:text-indigo-400"
                        />
                        <span className="text-[9px] text-slate-600 font-mono">Node {sel.nodeId} · {sel.field}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <label className={`flex items-center gap-2 text-[10px] uppercase font-bold cursor-pointer transition-colors ${sel.required !== false ? 'text-indigo-400' : 'text-slate-500'}`}>
                        <input 
                          type="checkbox" 
                          checked={sel.required !== false} 
                          onChange={(e) => updateSelection(idx, { required: e.target.checked })}
                          className="w-3.5 h-3.5 rounded border-white/10 bg-black/40 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        Required
                      </label>
                      <div className="flex items-center gap-2">
                        <button onClick={() => moveInput(idx, 'up')} className="p-2 bg-white/5 rounded-xl text-slate-500 hover:text-white"><ArrowUp className="w-4 h-4" /></button>
                        <button onClick={() => moveInput(idx, 'down')} className="p-2 bg-white/5 rounded-xl text-slate-500 hover:text-white"><ArrowDown className="w-4 h-4" /></button>
                      </div>
                    </div>
                  </div>
                ))}
                {selections.length === 0 && (
                  <div className="p-8 text-center border-2 border-dashed border-white/5 rounded-3xl text-slate-600 italic text-sm">
                    No inputs selected. Activate fields in Architect View first.
                  </div>
                )}
              </div>
          </div>

          <div className="space-y-6">
              <h4 className="text-xs font-black text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                <Type className="w-3 h-3" /> Action Buttons
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {uiConfig.buttons.map((btn: any, i: number) => (
                  <div key={i} className="p-4 bg-white/5 rounded-2xl border border-white/5 space-y-3">
                      <input value={btn.label} onChange={(e) => { const nb = [...uiConfig.buttons]; nb[i].label = e.target.value; setUiConfig({ ...uiConfig, buttons: nb }); }} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-xs text-white" />
                      <select value={btn.style} onChange={(e) => { const nb = [...uiConfig.buttons]; nb[i].style = e.target.value; setUiConfig({ ...uiConfig, buttons: nb }); }} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-[10px] text-slate-400 uppercase font-bold">
                        <option value="primary">Indigo (Primary)</option>
                        <option value="secondary">Grey (Secondary)</option>
                        <option value="success">Green (Success)</option>
                        <option value="danger">Red (Danger)</option>
                      </select>
                  </div>
                ))}
              </div>
          </div>
        </div>
      </div>

      {/* Preview Panel */}
      <div className="flex flex-col gap-6">
          <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 shadow-2xl overflow-hidden relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent pointer-events-none" />
            <h4 className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-6 text-center">Discord Response Preview</h4>
            <div className="flex justify-center">
                <div className="bg-[#313338] rounded-xl shadow-2xl border border-black/20 w-full max-w-sm overflow-hidden animate-in zoom-in duration-300">
                  <div className="p-4 space-y-4">
                      <div className="flex gap-3">
                        <div className="w-9 h-9 rounded-full bg-indigo-500 flex-shrink-0 flex items-center justify-center font-black text-white text-xs">A</div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5 mb-1">
                              <span className="text-[11px] font-bold text-white">Atlas Bot</span>
                              <span className="bg-[#5865F2] text-[8px] text-white px-1.5 rounded-sm font-black">BOT</span>
                            </div>
                            <div 
                              className="rounded-lg p-4 border-l-4 space-y-3"
                              style={{ backgroundColor: '#2b2d31', borderLeftColor: uiConfig.embed.color }}
                            >
                              <h5 className="text-[12px] font-bold text-white">{uiConfig.embed.title_template.replace('{user}', 'User')}</h5>
                              <div className="aspect-video w-full bg-black/20 rounded-lg flex items-center justify-center text-slate-600 text-[10px] italic">Generation Preview...</div>
                              <div className="grid grid-cols-2 gap-2">
                                  {uiConfig.embed.show_metadata.map((m: string) => (
                                    <div key={m} className="flex flex-col">
                                      <span className="text-[8px] text-slate-500 uppercase font-black">{m}</span>
                                      <span className="text-[9px] text-slate-300 font-medium">value_data</span>
                                    </div>
                                  ))}
                              </div>
                            </div>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 pl-12">
                        {uiConfig.buttons.map((btn: any, i: number) => (
                          <button 
                            key={i} 
                            className={`px-4 py-1.5 rounded text-[10px] font-black text-white transition-opacity hover:opacity-80 ${
                              btn.style === 'primary' ? 'bg-[#5865f2]' : 
                              btn.style === 'success' ? 'bg-[#248046]' :
                              btn.style === 'danger' ? 'bg-[#da373c]' : 'bg-[#4e5058]'
                            }`}
                          >
                            {btn.label}
                          </button>
                        ))}
                      </div>
                  </div>
                </div>
            </div>
          </div>
          
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-3xl p-6">
            <div className="flex gap-3 text-amber-500 mb-2">
                <Eye className="w-4 h-4" />
                <span className="text-xs font-black uppercase tracking-widest">Live Visualizer</span>
            </div>
            <p className="text-[10px] text-amber-500/60 leading-relaxed font-medium">
              Changes here update the Discord interaction manifest in real-time. This defines how users see your workflow outputs.
            </p>
          </div>
      </div>
    </div>
  );
}
