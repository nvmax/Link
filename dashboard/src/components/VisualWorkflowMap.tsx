"use client";

import React, { useRef, useState, useEffect } from 'react';
import { Maximize2, CheckSquare, Square, Check, Layers } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

const EMPTY_WORKFLOW = {};

export function VisualWorkflowMap() {
  const { 
    selectedWorkflow, 
    selections, 
    toggleInput, 
    loraFiles,
    loraSelections,
    setLoraSelections,
    objectInfo,
    updateWorkflowInput,
    updateSelection
  } = useDashboard();

  const workflow = selectedWorkflow?.content || EMPTY_WORKFLOW;

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 0.8 });
  const [isPanning, setIsPanning] = useState(false);
  const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 });
  const [coords, setCoords] = useState<Record<string, {x: number, y: number, w: number, h: number}>>({});
  const [lines, setLines] = useState<any[]>([]);

  useEffect(() => {
    const updateCoords = () => {
      const newCoords: Record<string, {x: number, y: number, w: number, h: number}> = {};
      Object.keys(workflow).forEach(id => {
        const el = document.getElementById(`node-${id}`);
        if (el) {
          newCoords[id] = {
            x: el.offsetLeft,
            y: el.offsetTop,
            w: el.offsetWidth,
            h: el.offsetHeight
          };
        }
      });
      setCoords(prev => {
        if (JSON.stringify(prev) === JSON.stringify(newCoords)) return prev;
        return newCoords;
      });
    };
    const timeout = setTimeout(updateCoords, 50);
    window.addEventListener('resize', updateCoords);
    return () => {
      clearTimeout(timeout);
      window.removeEventListener('resize', updateCoords);
    };
  }, [workflow, transform.scale]); // Re-calculate coords when scale changes might be needed if offsetLeft changes, but scale is on parent. So [workflow] is fine.

  useEffect(() => {
    const newLines: any[] = [];
    Object.keys(workflow).forEach(id => {
      const node = workflow[id];
      if (!coords[id]) return;
      
      const targetX = coords[id].x;
      const targetY = coords[id].y + 50;

      if (node.inputs) {
        Object.entries(node.inputs).forEach(([key, val], idx) => {
          if (Array.isArray(val)) {
            const sourceId = String(val[0]);
            if (coords[sourceId]) {
              const sourceX = coords[sourceId].x + coords[sourceId].w;
              const sourceY = coords[sourceId].y + 40;
              const yOffset = idx * 25;
              const x1 = sourceX;
              const y1 = sourceY;
              const x2 = targetX - 5;
              const y2 = targetY + yOffset;
              const cp1x = x1 + Math.abs(x2 - x1) / 2;
              const cp1y = y1;
              const cp2x = x2 - Math.abs(x2 - x1) / 2;
              const cp2y = y2;
              newLines.push({
                id: `${sourceId}-${id}-${key}`,
                path: `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`
              });
            }
          }
        });
      }
    });
    setLines(prev => {
      if (JSON.stringify(prev) === JSON.stringify(newLines)) return prev;
      return newLines;
    });
  }, [coords, workflow]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      setIsPanning(true);
      setLastMousePos({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      const dx = e.clientX - lastMousePos.x;
      const dy = e.clientY - lastMousePos.y;
      setTransform(prev => ({ ...prev, x: prev.x + dx, y: prev.y + dy }));
      setLastMousePos({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => setIsPanning(false);
  
  const handleWheel = (e: React.WheelEvent) => {
    const delta = e.deltaY > 0 ? 0.95 : 1.05;
    setTransform(prev => ({ ...prev, scale: Math.min(Math.max(prev.scale * delta, 0.1), 2) }));
  };

  const resetView = () => setTransform({ x: 0, y: 0, scale: 0.8 });

  const getLevels = () => {
    const levels: Record<string, number> = {};
    const visit = (id: string, level: number) => {
      levels[id] = Math.max(levels[id] || 0, level);
      if (workflow[id]?.inputs) {
        Object.values(workflow[id].inputs).forEach(val => {
          if (Array.isArray(val)) visit(String(val[0]), level + 1);
        });
      }
    };
    Object.keys(workflow).forEach(id => visit(id, 0));
    return levels;
  };

  const levels = getLevels();
  const sortedLevels = Array.from(new Set(Object.values(levels))).sort((a, b) => b - a);
  const columns: Record<number, string[]> = {};
  sortedLevels.forEach(l => {
    columns[l] = Object.keys(levels).filter(id => levels[id] === l);
  });

  if (!selectedWorkflow) {
    return <div className="h-full flex items-center justify-center text-slate-500">Select a workflow to view the visual map.</div>;
  }

  const handleLoraSelect = (nodeId: string, loraFileName: string) => {
    setLoraSelections({ ...loraSelections, [nodeId]: loraFileName });
  };

  return (
    <div 
      ref={containerRef} 
      className={`h-full overflow-hidden bg-[#0a0a0c] relative select-none rounded-3xl border border-white/5 shadow-2xl ${isPanning ? 'cursor-grabbing' : 'cursor-grab'}`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
       <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: `radial-gradient(circle, white 1px, transparent 1px)`, backgroundSize: `${40 * transform.scale}px ${40 * transform.scale}px`, backgroundPosition: `${transform.x}px ${transform.y}px` }}></div>
       <div ref={canvasRef} className="relative w-full h-full" style={{ transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`, transformOrigin: '0 0' }}>
          <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible" style={{ zIndex: 0 }}>
            {lines.map(line => (
              <g key={line.id}>
                <path d={line.path} fill="none" stroke="currentColor" strokeWidth="4" className="text-indigo-500/10" />
                <path d={line.path} fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-500/40 transition-all pointer-events-auto" style={{ animation: 'dash 20s linear infinite' }} strokeDasharray="5 5" />
              </g>
            ))}
          </svg>
          <div className="flex gap-24 p-60 relative z-10 w-max">
            {sortedLevels.map(lvl => (
              <div key={lvl} className="flex flex-col gap-12">
                {columns[lvl].map(id => {
                  const isLoraNode = workflow[id].class_type.toLowerCase().includes('lora');
                  return (
                    <div key={id} id={`node-${id}`} className="w-72 bg-[#111114]/80 backdrop-blur-md border border-white/5 rounded-3xl shadow-2xl overflow-visible hover:border-indigo-500/50 transition-all group relative">
                      <div className="bg-white/5 p-4 border-b border-white/5 flex items-center justify-between">
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{workflow[id].class_type}</span>
                        <span className="text-[8px] text-slate-600 font-mono">#{id}</span>
                      </div>
                      
                      {isLoraNode && (
                        <div className="p-4 border-b border-white/5 bg-indigo-500/5">
                          <label className="text-[9px] uppercase font-bold text-indigo-400 flex items-center gap-1.5 mb-2">
                            <Layers className="w-3 h-3" />
                            Assign LoRA List
                          </label>
                          <select 
                            value={loraSelections[id] || ''}
                            onChange={(e) => handleLoraSelect(id, e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-lg text-xs p-2 text-slate-300 outline-none focus:border-indigo-500/50"
                          >
                            <option value="">None (Default)</option>
                            {loraFiles.map(lf => (
                              <option key={lf.name} value={lf.name}>{lf.name}</option>
                            ))}
                          </select>
                        </div>
                      )}

                      <div className="p-4 space-y-3">
                        {Object.entries(workflow[id].inputs || {}).map(([key, val]: [string, any]) => {
                          const isSelected = selections.find(s => s.nodeId === id && s.field === key);
                          const inputType = typeof val === 'string' ? 'string' : 'number';
                          
                          // Skip inputs that are connected to other nodes
                          if (Array.isArray(val)) return null;

                          const nodeInfo = objectInfo?.[workflow[id].class_type];
                          const inputInfo = nodeInfo?.input?.required?.[key] || nodeInfo?.input?.optional?.[key];
                          const isDropdown = Array.isArray(inputInfo) && Array.isArray(inputInfo[0]);
                          const options = isDropdown ? inputInfo[0] : [];

                          return (
                            <div key={key} className={`flex flex-col p-3 rounded-2xl border transition-all ${isSelected ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-black/20 border-white/5'}`}>
                              <div className="flex items-center justify-between mb-2">
                                <label className={`text-[9px] uppercase font-bold ${isSelected ? 'text-indigo-400' : 'text-slate-500'}`}>{key}</label>
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
                                  className="w-full bg-black/40 border border-white/10 rounded-lg text-xs p-2 text-slate-300 outline-none focus:border-indigo-500/50"
                                  onMouseDown={(e) => e.stopPropagation()} // Prevent map pan when clicking select
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
                                  className="w-full bg-black/40 border border-white/10 rounded-lg text-xs p-2 text-slate-300 outline-none focus:border-indigo-500/50"
                                  onMouseDown={(e) => e.stopPropagation()} // Prevent map pan when clicking input
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
            ))}
          </div>
       </div>
       <div className="absolute bottom-6 right-6 flex flex-col gap-2 z-20">
         <button onClick={resetView} className="bg-[#1c1c21] border border-white/10 p-3 rounded-xl text-slate-400 hover:text-white hover:border-indigo-500/50 transition-all shadow-2xl"><Maximize2 className="w-4 h-4" /></button>
         <div className="bg-[#1c1c21] border border-white/10 px-3 py-1.5 rounded-xl text-[10px] font-mono text-slate-500 flex items-center justify-center shadow-2xl">{Math.round(transform.scale * 100)}%</div>
       </div>
       <style jsx>{` @keyframes dash { to { stroke-dashoffset: -10; } } `}</style>
    </div>
  );
}
