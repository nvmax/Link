"use client";

import React from 'react';
import { Type, CheckSquare, Square } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function ListView() {
  const { 
    config,
    selectedWorkflow, 
    selections, 
    toggleInput, 
    objectInfo,
    updateWorkflowInput,
    customCommandName,
    setCustomCommandName,
    loraFiles,
    loraSelections,
    setLoraSelections,
    updateSelection
  } = useDashboard();

  const isDomainConfigured = Boolean(config?.INPAINT_SERVER_DOMAIN && config.INPAINT_SERVER_DOMAIN.trim() !== '');

  if (!selectedWorkflow) {
    return <div className="h-full flex items-center justify-center text-slate-500">Select a workflow to view the list map.</div>;
  }

  const workflow = selectedWorkflow.content || {};

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {Object.entries(workflow).map(([id, node]: [string, any]) => {
        if (!node.inputs) return null;
        
        const hasVisibleInputs = Object.values(node.inputs).some(val => !Array.isArray(val));
        if (!hasVisibleInputs) return null;
        
        const isLoraNode = node.class_type?.toLowerCase().includes('lora') || false;

        return (
          <div key={id} className="bg-black/20 border border-white/5 rounded-3xl p-6 hover:border-white/10 transition-all group">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/5">
              <div className="flex flex-col">
                {node._meta?.title && (
                  <span className="text-sm font-black text-white mb-0.5">{node._meta.title}</span>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest opacity-80">{node.class_type}</span>
                  <span className="text-[9px] text-slate-500 font-mono">#{id}</span>
                </div>
              </div>
              {isLoraNode && (
                <div className="flex items-center gap-3">
                  <span className="text-[10px] uppercase font-bold text-slate-400">Assign LoRA List:</span>
                  <select 
                    value={loraSelections[id] || ''}
                    onChange={(e) => setLoraSelections({ ...loraSelections, [id]: e.target.value })}
                    className="bg-black/40 border border-white/10 rounded-lg text-xs p-1.5 text-slate-300 outline-none focus:border-indigo-500/50"
                  >
                    <option value="">None (Default)</option>
                    {loraFiles.map(lf => (
                      <option key={lf.name} value={lf.name}>{lf.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(node.inputs).map(([key, val]: [string, any]) => {
                if (Array.isArray(val)) return null;

                const isSelected = selections.find(s => s.nodeId === id && s.field === key);
                const inputType = typeof val === 'string' ? 'string' : 'number';
                
                const nodeInfo = objectInfo?.[node.class_type];
                const inputInfo = nodeInfo?.input?.required?.[key] || nodeInfo?.input?.optional?.[key];
                const isDropdown = Array.isArray(inputInfo) && (
                  Array.isArray(inputInfo[0]) || 
                  (inputInfo[1] && typeof inputInfo[1] === 'object' && Array.isArray(inputInfo[1].options))
                );
                const rawOptions = isDropdown ? (Array.isArray(inputInfo[0]) ? inputInfo[0] : inputInfo[1].options) : [];
                const options = rawOptions.map((opt: any) => {
                  if (opt && typeof opt === 'object') {
                    return String(opt.key !== undefined ? opt.key : (opt.value !== undefined ? opt.value : (opt.name !== undefined ? opt.name : JSON.stringify(opt))));
                  }
                  return String(opt);
                });

                return (
                  <div key={key} className={`flex flex-col p-4 rounded-2xl border transition-all ${isSelected ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-white/5 border-white/5 hover:bg-white/[0.07]'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <span className={`text-[10px] uppercase font-bold ${isSelected ? 'text-indigo-400' : 'text-slate-400'}`}>
                        {key}
                        {isSelected && (
                          <span className="text-[9px] text-slate-500 font-normal lowercase ml-2">
                            (resolves as: <span className="font-mono text-indigo-300 font-bold">{isSelected.id || isSelected.field}</span>)
                          </span>
                        )}
                      </span>
                      <div className="flex items-center gap-2">
                        {isSelected && (
                           <button
                              onClick={() => updateSelection(selections.indexOf(isSelected), { required: isSelected.required === false ? true : false })}
                              className={`text-[8px] px-1.5 py-0.5 rounded font-bold transition-colors ${isSelected.required !== false ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'bg-slate-500/20 text-slate-400 hover:bg-slate-500/30'}`}
                           >
                              {isSelected.required !== false ? 'REQUIRED' : 'OPTIONAL'}
                           </button>
                        )}
                        <button 
                          onClick={() => toggleInput(id, key, inputType)}
                          className={`flex items-center justify-center w-5 h-5 rounded transition-all ${isSelected ? 'bg-indigo-500 text-white shadow-[0_0_8px_rgba(99,102,241,0.4)]' : 'bg-white/5 text-slate-500 hover:bg-white/10'}`}
                        >
                          {isSelected ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>

                    {/* Discord Input Type panel — same as Visual Architect */}
                    {isSelected && (
                      <div className="mb-3 p-2 rounded-xl bg-black/40 border border-indigo-500/20 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[7px] font-bold text-slate-500 uppercase tracking-widest">ComfyUI type</span>
                          <span className="text-[7px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">
                            {(() => {
                              const ii = inputInfo;
                              if (!ii) return 'unknown';
                              if (Array.isArray(ii[0])) return `ENUM (${ii[0].length} options)`;
                              if (ii[1] && typeof ii[1] === 'object' && Array.isArray(ii[1].options)) {
                                  return `ENUM (${ii[1].options.length} options)`;
                              }
                              if (typeof ii[0] === 'string') return ii[0];
                              return 'unknown';
                            })()}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[7px] font-bold text-indigo-300/70 uppercase tracking-widest">Discord input type</span>
                          {['image_upload','audio_upload','video_upload'].includes(isSelected.type) && (
                            <span className="text-[7px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-bold">FILE → channel</span>
                          )}
                          {isSelected.type === 'text' && (
                            <span className="text-[7px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold">TEXT → modal</span>
                          )}
                          {isSelected.type === 'select' && (
                            <span className="text-[7px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold">SELECT → modal</span>
                          )}
                          {isSelected.type === 'inpaint' && (
                            <span className={`text-[7px] px-1.5 py-0.5 rounded font-bold ${isDomainConfigured ? 'bg-fuchsia-500/20 text-fuchsia-400' : 'bg-rose-500/20 text-rose-400'}`}>
                              {isDomainConfigured ? 'INPAINT → Activity' : '⚠️ INPAINT (Requires Domain in Mission Control)'}
                            </span>
                          )}
                        </div>
                        <select
                          value={isSelected.type || 'text'}
                          onChange={(e) => updateSelection(selections.indexOf(isSelected), { type: e.target.value })}
                          className="w-full bg-black/60 border border-indigo-500/30 rounded-lg text-[10px] px-2 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                        >
                          <option value="text">text — free text / prompt (modal)</option>
                          <option value="image_upload">image_upload — image file (channel)</option>
                          <option value="audio_upload">audio_upload — audio file (channel)</option>
                          <option value="video_upload">video_upload — video file (channel)</option>
                          <option value="inpaint" disabled={!isDomainConfigured}>
                            {isDomainConfigured ? "inpaint — interactive canvas (Activity)" : "🔒 inpaint (Requires Webserver Domain in Mission Control)"}
                          </option>
                          <option value="select">select — dropdown choices (modal)</option>
                        </select>
                        
                        <div className="mt-2 space-y-1">
                          <label className="text-[7px] font-bold text-indigo-300/70 uppercase tracking-widest block">Discord Parameter Name</label>
                          <input
                            type="text"
                            value={isSelected.id || ''}
                            onChange={(e) => {
                              const val = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_');
                              updateSelection(selections.indexOf(isSelected), { id: val });
                            }}
                            placeholder="e.g. prompt"
                            className="w-full bg-black/60 border border-indigo-500/30 rounded-lg text-[10px] px-2 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                          />
                        </div>
                        
                        <div className="mt-2 space-y-1">
                          <label className="text-[7px] font-bold text-indigo-300/70 uppercase tracking-widest block">Discord Display Label</label>
                          <input
                            type="text"
                            value={isSelected.label || ''}
                            onChange={(e) => {
                              updateSelection(selections.indexOf(isSelected), { label: e.target.value });
                            }}
                            placeholder="e.g. Prompt Text"
                            className="w-full bg-black/60 border border-indigo-500/30 rounded-lg text-[10px] px-2 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                          />
                        </div>

                        {isSelected.type === 'select' && (
                          <div className="mt-2 space-y-1">
                            <label className="text-[7px] font-bold text-indigo-300/70 uppercase tracking-widest block">Choices (comma-separated)</label>
                            <ChoicesInput
                              choices={isSelected.choices}
                              onChange={(arr) => {
                                updateSelection(selections.indexOf(isSelected), { choices: arr });
                              }}
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {isDropdown ? (
                      <select
                        value={val || ''}
                        onChange={(e) => updateWorkflowInput(id, key, e.target.value)}
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-300 outline-none focus:border-indigo-500/50"
                      >
                        {options.map((opt: string) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={typeof val === 'number' ? 'number' : 'text'}
                        value={val || ''}
                        onChange={(e) => updateWorkflowInput(id, key, typeof val === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)}
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-300 outline-none focus:border-indigo-500/50"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ChoicesInput({
  choices,
  onChange,
  onMouseDown
}: {
  choices?: any[];
  onChange: (choices: string[]) => void;
  onMouseDown?: (e: React.MouseEvent) => void;
}) {
  const formatChoices = (arr?: any[]): string => {
    if (!Array.isArray(arr)) return '';
    return arr.map(c => {
      if (c && typeof c === 'object') {
        return c.value !== undefined ? String(c.value) : (c.label !== undefined ? String(c.label) : JSON.stringify(c));
      }
      return String(c);
    }).join(', ');
  };

  const [rawText, setRawText] = React.useState<string>(() => formatChoices(choices));
  const isInternalChange = React.useRef(false);

  React.useEffect(() => {
    if (isInternalChange.current) {
      isInternalChange.current = false;
      return;
    }
    setRawText(formatChoices(choices));
  }, [choices]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    isInternalChange.current = true;
    setRawText(text);
    const arr = text.split(',').map(s => s.trim()).filter(Boolean);
    onChange(arr);
  };

  const handleBlur = () => {
    const arr = rawText.split(',').map(s => s.trim()).filter(Boolean);
    setRawText(arr.join(', '));
    onChange(arr);
  };

  return (
    <input
      type="text"
      value={rawText}
      onChange={handleChange}
      onBlur={handleBlur}
      onMouseDown={onMouseDown}
      placeholder="e.g. 5, 10, 15, 20"
      className="w-full bg-black/60 border border-indigo-500/30 rounded-lg text-[10px] px-2 py-1 text-slate-200 outline-none focus:border-indigo-500 font-mono"
    />
  );
}

