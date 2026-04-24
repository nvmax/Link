"use client";

import React from 'react';
import { Type, CheckSquare, Square } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function ListView() {
  const { 
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
        
        const isLoraNode = node.class_type.toLowerCase().includes('lora');

        return (
          <div key={id} className="bg-black/20 border border-white/5 rounded-3xl p-6 hover:border-white/10 transition-all group">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/5">
              <div className="flex flex-col">
                <span className="text-xs font-black text-indigo-400 uppercase tracking-widest">{node.class_type}</span>
                <span className="text-[10px] text-slate-500 font-mono">Node #{id}</span>
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
                const isDropdown = Array.isArray(inputInfo) && Array.isArray(inputInfo[0]);
                const options = isDropdown ? inputInfo[0] : [];

                return (
                  <div key={key} className={`flex flex-col p-4 rounded-2xl border transition-all ${isSelected ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-white/5 border-white/5 hover:bg-white/[0.07]'}`}>
                    <div className="flex items-center justify-between mb-3">
                      <span className={`text-[10px] uppercase font-bold ${isSelected ? 'text-indigo-400' : 'text-slate-400'}`}>{key}</span>
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

                    {isDropdown ? (
                      <select
                        value={val}
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
                        value={val}
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
