"use client";

import React from 'react';
import { Layout, List, Type, ArrowUp, ArrowDown, Eye, Plus, Trash2 } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function ModalStudio() {
  const { selections, updateSelection, moveInput, uiConfig, setUiConfig, workflows } = useDashboard();

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
                    value={uiConfig.embed?.title_template || ''}
                    onChange={(e) => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, title_template: e.target.value } })}
                    className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-xs text-white outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 uppercase font-bold">Accent Color</label>
                  <div className="flex gap-2">
                    <input type="color" value={uiConfig.embed?.color || '#5865F2'} onChange={(e) => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, color: e.target.value } })} className="w-10 h-10 rounded-lg bg-transparent border-none cursor-pointer" />
                    <input value={uiConfig.embed?.color || '#5865F2'} onChange={(e) => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, color: e.target.value } })} className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 text-xs font-mono text-white outline-none focus:border-indigo-500/50" />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 uppercase font-bold">Image Position</label>
                  <select 
                    value={uiConfig.embed?.image_position || 'top'} 
                    onChange={(e) => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, image_position: e.target.value } })}
                    className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-[10px] text-slate-400 font-bold"
                  >
                    <option value="top">Main (Top)</option>
                    <option value="bottom">Thumbnail (Bottom) do not use for video/audio modal</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 uppercase font-bold">Show Footer</label>
                  <div className="flex bg-black/40 p-1 rounded-xl border border-white/5 h-[34px]">
                    <button 
                      onClick={() => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, show_footer: true } })}
                      className={`flex-1 rounded-lg text-[8px] font-black transition-all ${uiConfig.embed?.show_footer !== false ? 'bg-indigo-500 text-white' : 'text-slate-500'}`}
                    >ON</button>
                    <button 
                      onClick={() => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, show_footer: false } })}
                      className={`flex-1 rounded-lg text-[8px] font-black transition-all ${uiConfig.embed?.show_footer === false ? 'bg-rose-500 text-white' : 'text-slate-500'}`}
                    >OFF</button>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] text-slate-500 uppercase font-bold">Show Author</label>
                  <div className="flex bg-black/40 p-1 rounded-xl border border-white/5 h-[34px]">
                    <button 
                      onClick={() => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, show_author: true } })}
                      className={`flex-1 rounded-lg text-[8px] font-black transition-all ${uiConfig.embed?.show_author !== false ? 'bg-indigo-500 text-white' : 'text-slate-500'}`}
                    >ON</button>
                    <button 
                      onClick={() => setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, show_author: false } })}
                      className={`flex-1 rounded-lg text-[8px] font-black transition-all ${uiConfig.embed?.show_author === false ? 'bg-rose-500 text-white' : 'text-slate-500'}`}
                    >OFF</button>
                  </div>
                </div>
              </div>
          </div>

          <div className="space-y-6">
              <h4 className="text-xs font-black text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                <Layout className="w-3 h-3" /> Display Metadata
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['prompt', 'seed', 'model', 'ratio', 'steps', 'sampler', 'cfg'].map((field) => (
                  <label key={field} className="flex items-center gap-2 bg-black/40 border border-white/5 rounded-xl p-3 cursor-pointer hover:border-indigo-500/50 transition-colors">
                    <input 
                      type="checkbox"
                      checked={uiConfig.embed?.show_metadata?.includes(field) || false}
                      onChange={(e) => {
                        const current = uiConfig.embed?.show_metadata || [];
                        const next = e.target.checked ? [...current, field] : current.filter((m: string) => m !== field);
                        setUiConfig({ ...uiConfig, embed: { ...uiConfig.embed, show_metadata: next } });
                      }}
                      className="w-4 h-4 rounded border-white/10 bg-black/40 text-indigo-500 focus:ring-0 focus:ring-offset-0"
                    />
                    <span className="text-xs font-bold text-slate-300 capitalize">{field}</span>
                  </label>
                ))}
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
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-black text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                  <Type className="w-3 h-3" /> Action Buttons
                </h4>
                <button 
                  onClick={() => setUiConfig({ ...uiConfig, buttons: [...uiConfig.buttons, { type: 'options', label: 'New Button', style: 'secondary' }] })}
                  className="bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-[10px] px-3 py-1.5 rounded-lg font-black transition-all flex items-center gap-2"
                >
                  <Plus className="w-3 h-3" /> Add Button
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {uiConfig.buttons.map((btn: any, i: number) => (
                  <div key={i} className="p-4 bg-white/5 rounded-2xl border border-white/5 space-y-3 relative group">
                      <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => { 
                            if(i > 0) {
                              const nb = [...uiConfig.buttons]; 
                              const temp = nb[i]; nb[i] = nb[i-1]; nb[i-1] = temp;
                              setUiConfig({ ...uiConfig, buttons: nb }); 
                            }
                          }}
                          className="p-1.5 bg-white/5 text-slate-400 hover:text-white rounded-lg transition-colors"
                        >
                          <ArrowUp className="w-3 h-3" />
                        </button>
                        <button 
                          onClick={() => { 
                            if(i < uiConfig.buttons.length - 1) {
                              const nb = [...uiConfig.buttons]; 
                              const temp = nb[i]; nb[i] = nb[i+1]; nb[i+1] = temp;
                              setUiConfig({ ...uiConfig, buttons: nb }); 
                            }
                          }}
                          className="p-1.5 bg-white/5 text-slate-400 hover:text-white rounded-lg transition-colors"
                        >
                          <ArrowDown className="w-3 h-3" />
                        </button>
                        <button 
                          onClick={() => { const nb = [...uiConfig.buttons]; nb.splice(i, 1); setUiConfig({ ...uiConfig, buttons: nb }); }}
                          className="p-1.5 bg-rose-500/10 text-rose-500 rounded-lg transition-colors hover:bg-rose-500/20"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                      
                      <div className="grid grid-cols-[1fr_2fr] gap-2 pt-2">
                        <div className="grid gap-1">
                          <label className="text-[8px] text-slate-500 uppercase font-bold">Emoji</label>
                          <select 
                            value={btn.emoji || ''} 
                            onChange={(e) => { const nb = [...uiConfig.buttons]; nb[i].emoji = e.target.value; setUiConfig({ ...uiConfig, buttons: nb }); }} 
                            className="w-full bg-black/40 border border-white/5 rounded-xl px-2 py-2 text-xs text-white"
                          >
                            <option value="">None</option>
                            <option value="🔄">🔄</option>
                            <option value="♻️">♻️</option>
                            <option value="🗑️">🗑️</option>
                            <option value="⚙️">⚙️</option>
                            <option value="🎬">🎬</option>
                            <option value="📸">📸</option>
                            <option value="🎨">🎨</option>
                            <option value="🪄">🪄</option>
                            <option value="🎲">🎲</option>
                            <option value="🔀">🔀</option>
                            <option value="✨">✨</option>
                            <option value="✅">✅</option>
                            <option value="❌">❌</option>
                            <option value="📖">📖</option>
                            <option value="🛠️">🛠️</option>
                            <option value="🚀">🚀</option>
                            <option value="♻">♻</option>
                            <option value="📐">📐</option>
                            <option value="📸">📸</option>
                            <option value="🎦">🎦</option>
                            <option value="⚡">⚡</option>
                            <option value="🧩">🧩</option>
                            <option value="🎲">🎲</option>
                            <option value="🎞️">🎞️</option>
                            <option value="📽️">📽️</option>
                            <option value="📚">📚</option>
                            <option value="🔧">🔧</option>
                          </select>
                        </div>
                        <div className="grid gap-1">
                          <label className="text-[8px] text-slate-500 uppercase font-bold">Button Label</label>
                          <input value={btn.label} onChange={(e) => { const nb = [...uiConfig.buttons]; nb[i].label = e.target.value; setUiConfig({ ...uiConfig, buttons: nb }); }} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-xs text-white" />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2">
                        <div className="grid gap-1">
                          <label className="text-[8px] text-slate-500 uppercase font-bold">Type</label>
                          <select value={btn.type} onChange={(e) => { const nb = [...uiConfig.buttons]; nb[i].type = e.target.value; setUiConfig({ ...uiConfig, buttons: nb }); }} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-[10px] text-slate-400 uppercase font-bold">
                            <option value="regenerate">Regenerate</option>
                            <option value="options">Options</option>
                            <option value="delete">Delete</option>
                            <option value="chain">Chain Workflow</option>
                          </select>
                        </div>
                        <div className="grid gap-1">
                          <label className="text-[8px] text-slate-500 uppercase font-bold">Style</label>
                          <select value={btn.style} onChange={(e) => { const nb = [...uiConfig.buttons]; nb[i].style = e.target.value; setUiConfig({ ...uiConfig, buttons: nb }); }} className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-[10px] text-slate-400 uppercase font-bold">
                            <option value="primary">Indigo</option>
                            <option value="secondary">Grey</option>
                            <option value="success">Green</option>
                            <option value="danger">Red</option>
                          </select>
                        </div>
                      </div>

                      {btn.type === 'chain' && (
                        <div className="grid gap-3 pt-2 border-t border-white/5">
                          <div className="grid gap-1">
                            <label className="text-[8px] text-amber-500 uppercase font-black">Target Workflow</label>
                            <select 
                              value={btn.target_workflow || ''} 
                              onChange={(e) => { const nb = [...uiConfig.buttons]; nb[i].target_workflow = e.target.value; setUiConfig({ ...uiConfig, buttons: nb }); }} 
                              className="w-full bg-black/40 border border-amber-500/20 rounded-xl px-3 py-2 text-[10px] text-white font-bold outline-none"
                            >
                              <option value="">Select Workflow...</option>
                              {workflows.map((wf: any) => (
                                <option key={wf.name} value={wf.name.replace(/\.json$/i, '')}>{wf.name.replace(/\.json$/i, '')}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      )}
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
                <div className="w-full max-w-sm space-y-2 animate-in zoom-in duration-300">
                  {uiConfig.embed?.image_position !== 'bottom' && (
                    <div className="aspect-video w-full bg-[#2b2d31] rounded-xl border border-white/5 flex items-center justify-center text-slate-500 text-[10px] italic shadow-xl mb-2">
                      Main Image Area (Attachment)
                    </div>
                  )}

                  <div 
                    className="bg-[#2b2d31] rounded-xl shadow-2xl border border-black/20 overflow-hidden"
                    style={{ borderLeft: `4px solid ${uiConfig.embed?.color || '#5865F2'}` }}
                  >
                    <div className="p-4 space-y-3">
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className="text-[11px] font-bold text-white">Link Bot</span>
                          <span className="bg-[#5865F2] text-[8px] text-white px-1.5 rounded-sm font-black uppercase">Bot</span>
                        </div>
                        
                        <div className="space-y-3">
                           <h5 className="text-[13px] font-black text-white">✨ {uiConfig.embed?.title_template?.replace('{user}', 'User') || 'User\'s Generation'}</h5>
                           
                           {/* Prompt Block */}
                           {uiConfig.embed?.show_metadata?.includes('prompt') && (
                             <div className="space-y-1">
                               <div className="text-[9px] text-slate-400 font-bold flex items-center gap-1">📝 Prompt:</div>
                               <div className="text-[10px] text-slate-200 bg-black/20 p-2 rounded-lg border border-white/5 italic leading-relaxed">a hyper-realistic high-detail photograph of the magma core workstation...</div>
                             </div>
                           )}

                           <div className="grid grid-cols-2 gap-3">
                               {uiConfig.embed?.show_metadata?.filter((m: string) => m !== 'prompt').map((m: string) => {
                                 const metaMap: any = {
                                   seed: { label: 'Seed', icon: '🎲' },
                                   model: { label: 'Model', icon: '🤖' },
                                   ratio: { label: 'Resolution', icon: '📐' },
                                   steps: { label: 'Steps', icon: '⏱️' }
                                 };
                                 const item = metaMap[m] || { label: m.toUpperCase(), icon: '🔹' };
                                 return (
                                   <div key={m} className="flex flex-col gap-0.5">
                                     <span className="text-[8px] text-slate-500 font-bold flex items-center gap-1">{item.icon} {item.label}:</span>
                                     <span className="text-[9px] text-slate-300 font-medium bg-black/10 px-1.5 py-0.5 rounded border border-white/5">value_data</span>
                                   </div>
                                 );
                               })}
                           </div>

                           {uiConfig.embed?.image_position === 'bottom' && (
                             <div className="aspect-video w-full bg-black/20 rounded-lg border border-white/5 flex items-center justify-center text-slate-500 text-[10px] italic mt-3 mb-1">
                               Main Image Area (Embed Image)
                             </div>
                           )}

                           {uiConfig.embed?.show_footer !== false && (
                             <div className="pt-2 border-t border-white/5 text-[8px] text-slate-500 font-medium italic">
                               Link | Profile: Standard | Job ID: 1df68cf7-ad75-46e5-b4be-32883c498fe9
                             </div>
                           )}
                        </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 pl-0 justify-center">
                    {uiConfig.buttons?.map((btn: any, i: number) => (
                      <button 
                        key={i} 
                        className={`px-3 py-1.5 rounded text-[10px] font-black text-white transition-opacity hover:opacity-80 shadow-lg ${
                          btn.style === 'primary' ? 'bg-[#5865f2]' : 
                          btn.style === 'success' ? 'bg-[#248046]' :
                          btn.style === 'danger' ? 'bg-[#da373c]' : 'bg-[#4e5058]'
                        }`}
                      >
                        {btn.emoji && <span className="mr-1.5">{btn.emoji}</span>}
                        {btn.label}
                      </button>
                    ))}
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
              Changes here update the Discord interaction manifest in real-time. This defines how users see your workflow outputs, must reboot bot for it to take effect in discord.
            </p>
          </div>
      </div>
    </div>
  );
}
