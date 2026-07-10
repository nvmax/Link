"use client";

import React from 'react';
import { Layers, ChevronRight, CheckCircle2, ArrowUp, ArrowDown, Trash2, Plus, ExternalLink, Activity, Tag, Info, Power, ChevronLeft, Folder, FolderPlus } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function LoraStudio() {
  const { 
    loraFiles, 
    editingLoraFile, 
    setEditingLoraFile,
    loadLoraFile, 
    saveLoraFile, 
    updateLoraField, 
    moveLora, 
    deleteLora, 
    addLora,
    createNewLoraList,
    deleteLoraList
  } = useDashboard();

  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(null);
  const [pickingForIdx, setPickingForIdx] = React.useState<number | null>(null);
  const [creatingInCategory, setCreatingInCategory] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const xc = rect.width / 2;
    const yc = rect.height / 2;
    const rotateX = ((yc - y) / yc) * 12;
    const rotateY = ((x - xc) / xc) * 12;
    
    card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
    card.style.setProperty('--glare-x', `${(x / rect.width) * 100}%`);
    card.style.setProperty('--glare-y', `${(y / rect.height) * 100}%`);
    card.style.setProperty('--glare-opacity', '0.12');
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    const card = e.currentTarget;
    card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
    card.style.setProperty('--glare-opacity', '0');
  };

  // Reset category view when switching files
  React.useEffect(() => {
    setSelectedCategory(null);
  }, [editingLoraFile?.name]);

  const categories = React.useMemo<string[]>(() => {
    if (!editingLoraFile?.content) return [];
    const cats = new Set<string>(editingLoraFile.content.map((l: any) => l.category || 'Uncategorized'));
    return Array.from(cats).sort();
  }, [editingLoraFile?.content]);

  const filteredLora = React.useMemo<any[]>(() => {
    if (!editingLoraFile?.content) return [];
    if (!selectedCategory) return [];
    return editingLoraFile.content.map((l: any, originalIndex: number) => ({ ...l, originalIndex }))
      .filter((l: any) => (l.category || 'Uncategorized') === selectedCategory);
  }, [editingLoraFile?.content, selectedCategory]);

  const handleAddCategory = () => {
    const name = prompt("Enter new category name:");
    if (name) {
      // Just set the category and it will show up in the grid
      setSelectedCategory(name);
    }
  };

  const handleFilePick = (idx: number | null) => {
    setPickingForIdx(idx);
    if (idx === null) {
      setCreatingInCategory(selectedCategory || 'Uncategorized');
    }
    fileInputRef.current?.click();
  };

  const onFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
      const capitalized = cleanName.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

      if (pickingForIdx !== null) {
        updateLoraField(pickingForIdx, 'file', file.name);
        // Auto-generate a nice display name if it's default
        const currentLora = editingLoraFile.content[pickingForIdx];
        if (!currentLora.name || currentLora.name.startsWith("New LoRA")) {
          updateLoraField(pickingForIdx, 'name', capitalized);
        }
      } else if (creatingInCategory !== null) {
        addLora({ 
          category: creatingInCategory, 
          file: file.name, 
          name: capitalized 
        });
      }
    }
    setPickingForIdx(null);
    setCreatingInCategory(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="flex flex-col lg:flex-row gap-8 h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={onFileSelected} 
        className="hidden" 
        accept=".safetensors,.ckpt,.pt"
      />
      <div className="w-full lg:w-[300px] flex flex-col gap-4 h-full shrink-0">
        <h3 className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-2">LoRA Lists</h3>
        <div className="flex-1 space-y-2 overflow-y-auto max-h-[200px] lg:max-h-none pr-2">
          {loraFiles.map((file) => (
            <div key={file.name} className="group/file flex items-center gap-2">
              <button 
                onClick={() => loadLoraFile(file)}
                className={`flex-1 flex items-center justify-between p-4 rounded-2xl transition-all border ${editingLoraFile?.name === file.name ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 shadow-xl shadow-amber-500/5' : 'bg-[#141418] border-white/5 text-slate-400 hover:bg-white/5'}`}
              >
                <div className="flex items-center gap-3">
                  <Layers className="w-4 h-4" />
                  <span className="text-sm font-medium">{file.name}</span>
                </div>
                <ChevronRight className={`w-4 h-4 transition-transform ${editingLoraFile?.name === file.name ? 'rotate-90' : ''}`} />
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); deleteLoraList(file); }}
                className="p-3 rounded-xl bg-white/5 text-slate-600 hover:bg-rose-500 hover:text-white transition-all opacity-0 group-hover/file:opacity-100"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
          {loraFiles.length === 0 && (
            <div className="p-4 text-xs text-slate-500 italic text-center">
              No LoRA files found.
            </div>
          )}
        </div>
        
        <button 
          onClick={createNewLoraList}
          className="w-full flex items-center justify-center gap-2 p-4 rounded-2xl bg-white/5 border border-dashed border-white/10 text-slate-400 hover:text-amber-500 hover:border-amber-500/30 transition-all mt-auto group"
        >
          <Plus className="w-4 h-4 group-hover:scale-125 transition-transform" />
          <span className="text-sm font-bold">New LoRA List</span>
        </button>
      </div>

      <div className="flex-1 bg-[#0d0d0f] rounded-3xl border border-white/5 overflow-hidden flex flex-col relative shadow-2xl min-h-[500px]">
          {editingLoraFile ? (
            <div className="flex-1 flex flex-col h-full overflow-hidden">
              <div className="p-4 sm:p-6 border-b border-white/5 flex flex-col sm:flex-row items-center justify-between bg-black/20 backdrop-blur-xl shrink-0 gap-4">
                <div className="flex items-center gap-4">
                  {selectedCategory && (
                    <button 
                      onClick={() => setSelectedCategory(null)}
                      className="p-2 bg-white/5 rounded-xl text-slate-400 hover:text-white transition-all border border-white/5"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                  )}
                  <div className="flex flex-col">
                    <span className="text-xs text-slate-500 font-bold uppercase tracking-widest">
                      {selectedCategory ? `${editingLoraFile.name} › ${selectedCategory}` : 'Select a Category'}
                    </span>
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-black text-white">
                        {selectedCategory || editingLoraFile.name}
                      </h3>
                      {selectedCategory && (
                        <button 
                          onClick={() => {
                            const newName = prompt("Rename this category/folder to:", selectedCategory);
                            if (newName && newName.trim() !== selectedCategory) {
                              const trimmed = newName.trim();
                              const newContent = editingLoraFile.content.map((lora: any) => {
                                if ((lora.category || 'Uncategorized') === selectedCategory) {
                                  return { ...lora, category: trimmed };
                                }
                                return lora;
                              });
                              setEditingLoraFile({ ...editingLoraFile, content: newContent });
                              setSelectedCategory(trimmed);
                            }
                          }}
                          className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 hover:text-amber-400 text-slate-400 text-[10px] font-bold tracking-wider uppercase transition-all border border-white/5"
                          title="Rename Folder / Category"
                        >
                          Rename Folder
                        </button>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={saveLoraFile} className="flex items-center gap-2 bg-amber-500 text-black px-6 py-2.5 rounded-xl font-black text-sm hover:bg-amber-400 transition-all shadow-xl shadow-amber-500/20 active:scale-95">
                    <CheckCircle2 className="w-4 h-4" />
                    Save Changes
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 sm:p-8 scrollbar-hide">
                  {!selectedCategory ? (
                    // Category Grid View
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                      {categories.map(cat => (
                        <button
                          key={cat}
                          onClick={() => setSelectedCategory(cat)}
                          onMouseMove={handleMouseMove}
                          onMouseLeave={handleMouseLeave}
                          className="group p-8 bg-white/5 border border-white/5 rounded-3xl hover:border-amber-500/30 transition-all text-left flex flex-col gap-4 relative overflow-hidden"
                          style={{
                            transformStyle: 'preserve-3d',
                            transition: 'transform 0.1s ease-out, border-color 0.3s ease-out, box-shadow 0.3s ease-out',
                          }}
                        >
                          <div 
                            className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity"
                            style={{ transform: 'translateZ(10px)' }}
                          >
                            <Folder className="w-24 h-24 rotate-12" />
                          </div>
                          <div 
                            className="w-12 h-12 rounded-2xl bg-amber-500/10 flex items-center justify-center text-amber-500 group-hover:bg-amber-500 group-hover:text-black transition-all"
                            style={{ transform: 'translateZ(30px)' }}
                          >
                            <Folder className="w-6 h-6" />
                          </div>
                          <div style={{ transform: 'translateZ(20px)' }}>
                            <h4 className="font-black text-white text-lg group-hover:text-amber-400 transition-colors">{cat}</h4>
                            <p className="text-xs text-slate-500 mt-1 font-bold uppercase tracking-widest">
                              {editingLoraFile.content.filter((l: any) => (l.category || 'Uncategorized') === cat).length} LoRAs
                            </p>
                          </div>
                          {/* Dynamic Glare Overlay */}
                          <div 
                            className="absolute inset-0 pointer-events-none transition-opacity duration-300 opacity-0 group-hover:opacity-100"
                            style={{
                              background: 'radial-gradient(circle at var(--glare-x, 50%) var(--glare-y, 50%), rgba(245, 158, 11, var(--glare-opacity, 0)) 0%, transparent 60%)',
                            }}
                          />
                        </button>
                      ))}
                      
                      <button 
                        onClick={handleAddCategory}
                        onMouseMove={handleMouseMove}
                        onMouseLeave={handleMouseLeave}
                        className="p-8 border-2 border-dashed border-white/10 rounded-3xl text-amber-500/50 hover:border-amber-500/30 hover:text-amber-400 transition-all flex flex-col items-center justify-center gap-3 group bg-amber-500/5 relative overflow-hidden"
                        style={{
                          transformStyle: 'preserve-3d',
                          transition: 'transform 0.1s ease-out, border-color 0.3s ease-out, box-shadow 0.3s ease-out',
                        }}
                      >
                        <div 
                          className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center group-hover:bg-amber-500/20"
                          style={{ transform: 'translateZ(30px)' }}
                        >
                          <FolderPlus className="w-6 h-6" />
                        </div>
                        <span 
                          className="text-xs font-bold uppercase tracking-widest"
                          style={{ transform: 'translateZ(20px)' }}
                        >
                          Create New Category
                        </span>
                        {/* Dynamic Glare Overlay */}
                        <div 
                          className="absolute inset-0 pointer-events-none transition-opacity duration-300 opacity-0 group-hover:opacity-100"
                          style={{
                            background: 'radial-gradient(circle at var(--glare-x, 50%) var(--glare-y, 50%), rgba(245, 158, 11, var(--glare-opacity, 0)) 0%, transparent 60%)',
                          }}
                        />
                      </button>

                      <button 
                        onClick={() => handleFilePick(null)}
                        onMouseMove={handleMouseMove}
                        onMouseLeave={handleMouseLeave}
                        className="p-8 border-2 border-dashed border-white/5 rounded-3xl text-slate-500 hover:border-white/20 hover:text-white transition-all flex flex-col items-center justify-center gap-3 group relative overflow-hidden"
                        style={{
                          transformStyle: 'preserve-3d',
                          transition: 'transform 0.1s ease-out, border-color 0.3s ease-out, box-shadow 0.3s ease-out',
                        }}
                      >
                        <div 
                          className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-white/10"
                          style={{ transform: 'translateZ(30px)' }}
                        >
                          <Plus className="w-6 h-6" />
                        </div>
                        <span 
                          className="text-xs font-bold uppercase tracking-widest"
                          style={{ transform: 'translateZ(20px)' }}
                        >
                          Add LoRA (Uncategorized)
                        </span>
                        {/* Dynamic Glare Overlay */}
                        <div 
                          className="absolute inset-0 pointer-events-none transition-opacity duration-300 opacity-0 group-hover:opacity-100"
                          style={{
                            background: 'radial-gradient(circle at var(--glare-x, 50%) var(--glare-y, 50%), rgba(255, 255, 255, var(--glare-opacity, 0)) 0%, transparent 60%)',
                          }}
                        />
                      </button>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-24">
                      <button 
                        onClick={() => handleFilePick(null)}
                        className="col-span-1 xl:col-span-2 p-5 border-2 border-dashed border-white/5 rounded-3xl text-slate-400 hover:border-amber-500/30 hover:text-amber-400 hover:bg-amber-500/5 transition-all flex items-center justify-center gap-3 group active:scale-[0.99]"
                      >
                        <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
                          <Plus className="w-4 h-4 group-hover:scale-110 transition-transform" />
                        </div>
                        <span className="text-xs font-bold uppercase tracking-widest">Add LoRA to {selectedCategory}</span>
                      </button>

                      {filteredLora.length === 0 && (
                        <div className="col-span-1 xl:col-span-2 flex flex-col items-center justify-center py-20 bg-white/5 rounded-3xl border border-dashed border-white/10 text-slate-600">
                           <Layers className="w-12 h-12 mb-4 opacity-20" />
                           <p className="text-sm font-medium italic">This category is currently empty.</p>
                           <p className="text-[10px] uppercase tracking-widest mt-1 opacity-50 font-bold">Use the button above to add your first LoRA</p>
                        </div>
                      )}
                      
                      {filteredLora.map((lora: any) => {
                        const idx = lora.originalIndex;
                        return (
                          <div key={idx} className={`group p-5 rounded-2xl border transition-all shadow-lg ${lora.is_active === false ? 'bg-black/10 border-white/5 grayscale opacity-60' : 'bg-white/5 border-white/5 hover:border-amber-500/30 hover:shadow-amber-500/5'}`}>
                            
                            <div className="flex items-start justify-between mb-3">
                              <div className="flex-1 mr-4">
                                <input 
                                  value={lora.name || ''} 
                                  onChange={(e) => updateLoraField(idx, 'name', e.target.value)} 
                                  placeholder="LoRA Name (Display)"
                                  className="w-full bg-transparent border-none text-base font-black text-white focus:text-amber-400 outline-none p-0 placeholder:text-white/10" 
                                />
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className="text-[10px] font-mono text-amber-500/50 uppercase tracking-tighter">File:</span>
                                  <div className="flex-1 flex items-center gap-2">
                                    <input 
                                      value={lora.file || ''} 
                                      onChange={(e) => updateLoraField(idx, 'file', e.target.value)} 
                                      placeholder="filename.safetensors"
                                      className="flex-1 bg-transparent border-none text-[10px] font-mono text-slate-500 focus:text-slate-300 outline-none p-0" 
                                    />
                                    <button 
                                      onClick={() => handleFilePick(idx)}
                                      className="p-1 rounded bg-white/5 text-amber-500/50 hover:text-amber-400 hover:bg-white/10 transition-all"
                                      title="Pick file from computer"
                                    >
                                      <Folder className="w-3 h-3" />
                                    </button>
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-1.5">
                                <button 
                                  onClick={() => updateLoraField(idx, 'is_active', lora.is_active === false ? true : false)}
                                  className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-[9px] font-bold transition-all border ${lora.is_active !== false ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-slate-800 border-white/10 text-slate-500'}`}
                                >
                                  <Power className="w-2.5 h-2.5" />
                                  {lora.is_active !== false ? 'ACTIVE' : 'INACTIVE'}
                                </button>
                                <div className="flex items-center gap-0.5 bg-black/40 rounded-lg p-0.5 border border-white/5">
                                  <button onClick={() => moveLora(idx, 'up')} className="p-1 text-slate-500 hover:text-white transition-colors" disabled={idx === 0}><ArrowUp className="w-3 h-3" /></button>
                                  <button onClick={() => moveLora(idx, 'down')} className="p-1 text-slate-500 hover:text-white transition-colors" disabled={idx === editingLoraFile.content.length - 1}><ArrowDown className="w-3 h-3" /></button>
                                  <button onClick={() => deleteLora(idx)} className="p-1 text-rose-500/50 hover:text-rose-500 transition-colors ml-0.5"><Trash2 className="w-3 h-3" /></button>
                                </div>
                              </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
                              <div className="space-y-1.5">
                                <div className="flex items-center gap-1.5 text-slate-500">
                                  <Activity className="w-3 h-3" />
                                  <label className="text-[9px] uppercase font-bold tracking-widest">Weight</label>
                                </div>
                                <input 
                                  type="number" 
                                  step="0.05"
                                  value={lora.weight || 1.0} 
                                  onChange={(e) => updateLoraField(idx, 'weight', parseFloat(e.target.value))} 
                                  className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-xs font-bold text-amber-400 focus:border-amber-500/50 outline-none transition-all duration-300 focus:bg-amber-500/5" 
                                />
                              </div>
                              <div className="space-y-1.5">
                                <div className="flex items-center gap-1.5 text-slate-500">
                                  <Tag className="w-3 h-3" />
                                  <label className="text-[9px] uppercase font-bold tracking-widest">Category</label>
                                </div>
                                <select 
                                  value={lora.category || 'Uncategorized'} 
                                  onChange={(e) => {
                                    const val = e.target.value;
                                    if (val === '__new__') {
                                      const newCat = prompt("Enter new category name:");
                                      if (newCat && newCat.trim()) {
                                        updateLoraField(idx, 'category', newCat.trim());
                                      }
                                    } else {
                                      updateLoraField(idx, 'category', val === 'Uncategorized' ? '' : val);
                                    }
                                  }} 
                                  className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-xs text-slate-300 focus:border-amber-500/50 outline-none transition-all duration-300 focus:bg-amber-500/5"
                                >
                                  {categories.map(c => (
                                    <option key={c} value={c}>{c}</option>
                                  ))}
                                  <option value="__new__">+ New Category...</option>
                                </select>
                              </div>
                              <div className="space-y-1.5">
                                <div className="flex items-center gap-1.5 text-slate-500">
                                  <ExternalLink className="w-3 h-3" />
                                  <label className="text-[9px] uppercase font-bold tracking-widest">Civitai URL</label>
                                </div>
                                <div className="relative group/link">
                                  <input 
                                    value={lora.url || ''} 
                                    onChange={(e) => updateLoraField(idx, 'url', e.target.value)} 
                                    className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-xs text-slate-500 focus:text-indigo-400 focus:border-indigo-500/50 outline-none pr-10 transition-all duration-300 focus:bg-indigo-500/5" 
                                    placeholder="https://..."
                                  />
                                  {lora.url && (
                                    <a href={lora.url} target="_blank" rel="noreferrer" className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-indigo-400 transition-colors">
                                      <ExternalLink className="w-3.5 h-3.5" />
                                    </a>
                                  )}
                                </div>
                              </div>
                            </div>

                            <div className="space-y-3">
                              <div className="space-y-1.5">
                                <div className="flex items-center gap-1.5 text-slate-500">
                                  <Info className="w-3 h-3" />
                                  <label className="text-[9px] uppercase font-bold tracking-widest">Description</label>
                                </div>
                                <input 
                                  value={lora.description || ''} 
                                  onChange={(e) => updateLoraField(idx, 'description', e.target.value)} 
                                  className="w-full bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-xs text-slate-400 focus:text-slate-200 focus:border-amber-500/50 outline-none transition-all duration-300 focus:bg-amber-500/5" 
                                  placeholder="What does this LoRA do?"
                                />
                              </div>
                              <div className="space-y-1.5">
                                <div className="flex items-center gap-1.5 text-emerald-500/70">
                                  <Layers className="w-3 h-3" />
                                  <label className="text-[9px] uppercase font-bold tracking-widest">Trigger Prompt (Appended Automatically)</label>
                                </div>
                                <textarea 
                                  value={lora.add_prompt || ''} 
                                  onChange={(e) => updateLoraField(idx, 'add_prompt', e.target.value)} 
                                  className="w-full min-h-[60px] bg-black/40 border border-white/5 rounded-xl px-3 py-2 text-xs text-emerald-400/90 focus:border-emerald-500/50 outline-none resize-none scrollbar-hide transition-all duration-300 focus:bg-emerald-500/5"
                                  placeholder="e.g. style of van gogh, oil painting..."
                                ></textarea>
                              </div>
                            </div>

                          </div>
                        );
                      })}
                    </div>
                  )}
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
