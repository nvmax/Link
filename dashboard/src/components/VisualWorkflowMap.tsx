"use client";

import React, { useRef, useState, useEffect, useMemo } from 'react';
import { Maximize2, CheckSquare, Square, Check, Layers, CheckCircle2, Trash2 } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

const EMPTY_WORKFLOW = {};

export function VisualWorkflowMap() {
  const { 
    selectedWorkflow, 
    setSelectedWorkflow,
    selections, 
    toggleInput, 
    loraFiles,
    loraSelections,
    setLoraSelections,
    objectInfo,
    updateWorkflowInput,
    updateSelection,
    updateLoraSelection,
    nodeCoords,
    setNodeCoords
  } = useDashboard();

  const workflow = selectedWorkflow?.content || EMPTY_WORKFLOW;

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 0.6 });
  const [isPanning, setIsPanning] = useState(false);
  const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 });
  const [activeWire, setActiveWire] = useState<{ 
    type: 'input' | 'output',
    nodeId: string, 
    field?: string, 
    outputIndex?: number,
    startPos: { x: number, y: number } 
  } | null>(null);
  const [draggingNode, setDraggingNode] = useState<{ nodeId: string, offset: { x: number, y: number } } | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const renderedLines = useMemo(() => {
    const newLines: any[] = [];
    Object.entries(workflow).forEach(([id, node]: [string, any]) => {
      Object.entries(node.inputs || {}).forEach(([inputKey, val], inputIdx) => {
        if (Array.isArray(val)) {
          const sourceId = String(val[0]);
          const sourceIndex = val[1];
          const startPos = nodeCoords[id];
          const endPos = nodeCoords[sourceId];
          
          if (startPos && endPos) {
            // Target (Input) - on the left
            const targetX = startPos.x;
            const targetY = startPos.y + 65 + (inputIdx * 45); // Approximate vertical pos of input socket
            
            // Source (Output) - on the right
            const sourceX = endPos.x + 288;
            const sourceY = endPos.y + 65 + (sourceIndex * 30); // Approximate vertical pos of output port
            
            newLines.push({
              id: `${id}-${inputKey}-${sourceId}`,
              path: `M ${targetX} ${targetY} C ${targetX - 100} ${targetY}, ${sourceX + 100} ${sourceY}, ${sourceX} ${sourceY}`
            });
          }
        }
      });
    });
    return newLines;
  }, [workflow, nodeCoords]);

  const handleMouseDown = (e: React.MouseEvent) => {
    // Allow panning with Left Click (0) if we're clicking the background container or the canvas itself
    // We check if the target is not a button or input or part of a node card
    const target = e.target as HTMLElement;
    const isNodeUI = target.closest('.group.relative') || target.closest('button') || target.closest('select') || target.closest('input');
    const isBackground = !isNodeUI;
    
    if (e.button === 1 || e.button === 2 || (e.button === 0 && (e.altKey || isBackground))) {
      setIsPanning(true);
      setLastMousePos({ x: e.clientX, y: e.clientY });
      
      // Prevent native drag-and-drop and text selection
      e.preventDefault();
    }
  };

  const draggingRef = useRef<{ nodeId: string, offset: { x: number, y: number } } | null>(null);

  useEffect(() => {
    let frameId: number;

    const handleGlobalMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY });
      
      if (!isPanning && !draggingNode && !activeWire) return;

      frameId = requestAnimationFrame(() => {
        if (isPanning) {
          const dx = e.clientX - lastMousePos.x;
          const dy = e.clientY - lastMousePos.y;
          setTransform(prev => ({ ...prev, x: prev.x + dx, y: prev.y + dy }));
          setLastMousePos({ x: e.clientX, y: e.clientY });
        }

        if (draggingNode) {
          const rect = containerRef.current?.getBoundingClientRect();
          if (rect) {
            const x = (e.clientX - rect.left - transform.x) / transform.scale - draggingNode.offset.x;
            const y = (e.clientY - rect.top - transform.y) / transform.scale - draggingNode.offset.y;
            setNodeCoords(prev => ({ ...prev, [draggingNode.nodeId]: { x, y } }));
          }
        }
      });
    };

    const handleGlobalMouseUp = (e: MouseEvent) => {
      if (activeWire) {
        // Find if we are over a specific handle
        const target = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement;
        const inputHandle = target?.closest('[data-input-node]');
        const outputHandle = target?.closest('[data-output-node]');

        if (activeWire.type === 'output' && inputHandle) {
          const targetNodeId = inputHandle.getAttribute('data-input-node')!;
          const targetField = inputHandle.getAttribute('data-input-field')!;
          handleConnect(activeWire.nodeId, activeWire.outputIndex || 0, targetNodeId, targetField);
        } else if (activeWire.type === 'input' && outputHandle) {
          const sourceNodeId = outputHandle.getAttribute('data-output-node')!;
          const sourceIndex = parseInt(outputHandle.getAttribute('data-output-index') || '0');
          handleConnect(sourceNodeId, sourceIndex, activeWire.nodeId, activeWire.field!);
        } else {
          // Dropped on background
          if (activeWire.type === 'input') {
            handleWireDrop(null); // Disconnect
          }
        }
      }
      setIsPanning(false);
      setActiveWire(null);
      setDraggingNode(null);
    };

    window.addEventListener('mousemove', handleGlobalMouseMove);
    window.addEventListener('mouseup', handleGlobalMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleGlobalMouseMove);
      window.removeEventListener('mouseup', handleGlobalMouseUp);
      cancelAnimationFrame(frameId);
    };
  }, [isPanning, draggingNode, activeWire, lastMousePos, transform, mousePos]);

  // Initialize node coordinates if not set
  useEffect(() => {
    const levels = getLevels();
    const sortedLevels = Array.from(new Set(Object.values(levels))).sort((a, b) => b - a);
    const initialCoords: Record<string, { x: number, y: number }> = {};
    
    sortedLevels.forEach((lvl, colIdx) => {
      const nodesInCol = Object.keys(levels).filter(id => levels[id] === lvl);
      nodesInCol.forEach((id, rowIdx) => {
        if (!nodeCoords[id]) {
          initialCoords[id] = { x: colIdx * 500 + 100, y: rowIdx * 600 + 100 };
        }
      });
    });
    
    if (Object.keys(initialCoords).length > 0) {
      setNodeCoords(prev => ({ ...prev, ...initialCoords }));
    }
  }, [selectedWorkflow?.name]);

  const handleNodeDragStart = (nodeId: string, e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left click
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const offset = {
      x: (e.clientX - rect.left) / transform.scale,
      y: (e.clientY - rect.top) / transform.scale
    };
    setDraggingNode({ nodeId, offset });
    e.stopPropagation();
  };

  const handleConnect = (sourceId: string, sourceIndex: number, targetId: string, targetField: string) => {
    if (!selectedWorkflow) return;
    const newWorkflow = JSON.parse(JSON.stringify(workflow));
    if (newWorkflow[targetId]?.inputs) {
      newWorkflow[targetId].inputs[targetField] = [sourceId, sourceIndex];
      setSelectedWorkflow({ ...selectedWorkflow, content: newWorkflow });
    }
  };

  const handleWireStart = (nodeId: string, field: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const currentVal = workflow[nodeId]?.inputs[field];
    if (Array.isArray(currentVal) && selectedWorkflow) {
      const newWorkflow = JSON.parse(JSON.stringify(workflow));
      newWorkflow[nodeId].inputs[field] = ""; 
      setSelectedWorkflow({ ...selectedWorkflow, content: newWorkflow });
    }
    setActiveWire({ type: 'input', nodeId, field, startPos: { x: e.clientX, y: e.clientY } });
  };

  const handleOutputWireStart = (nodeId: string, outputIndex: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveWire({ type: 'output', nodeId, outputIndex, startPos: { x: e.clientX, y: e.clientY } });
  };

  const handleWireDrop = (targetNodeId: string | null, outputIndex: number = 0) => {
    if (!activeWire || !selectedWorkflow) return;
    if (activeWire.type !== 'input') return; // Only inputs can be "dropped" into empty space to disconnect

    const newWorkflow = JSON.parse(JSON.stringify(workflow));
    if (newWorkflow[activeWire.nodeId]?.inputs) {
      if (targetNodeId) {
        newWorkflow[activeWire.nodeId].inputs[activeWire.field!] = [targetNodeId, outputIndex];
      } else {
        newWorkflow[activeWire.nodeId].inputs[activeWire.field!] = ""; 
      }
      setSelectedWorkflow({ ...selectedWorkflow, content: newWorkflow });
    }
    setActiveWire(null);
  };
  
  const handleWheel = (e: React.WheelEvent) => {
    // Zoom relative to mouse position
    const zoomSpeed = 0.001;
    const delta = -e.deltaY;
    const newScale = Math.min(Math.max(transform.scale + delta * zoomSpeed, 0.1), 3);
    
    // Calculate new X/Y to zoom towards cursor
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const scaleRatio = newScale / transform.scale;
    
    setTransform(prev => ({
      ...prev,
      scale: newScale,
      x: mouseX - (mouseX - prev.x) * scaleRatio,
      y: mouseY - (mouseY - prev.y) * scaleRatio
    }));
  };

  const resetView = () => setTransform({ x: 0, y: 0, scale: 0.6 });

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

  const reachableNodes = useMemo(() => {
    const reachable = new Set<string>();
    // Identify terminal nodes (not referenced as inputs)
    const referenced = new Set<string>();
    Object.values(workflow).forEach((node: any) => {
      Object.values(node.inputs || {}).forEach((val: any) => {
        if (Array.isArray(val)) referenced.add(String(val[0]));
      });
    });
    
    const terminals = Object.keys(workflow).filter(id => !referenced.has(id));
    const stack = [...terminals];
    
    while (stack.length > 0) {
      const id = stack.pop()!;
      if (reachable.has(id)) continue;
      reachable.add(id);
      const node = workflow[id];
      if (node?.inputs) {
        Object.values(node.inputs).forEach((val: any) => {
          if (Array.isArray(val)) stack.push(String(val[0]));
        });
      }
    }
    return reachable;
  }, [workflow]);

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
      onWheel={handleWheel}
      onContextMenu={(e) => e.preventDefault()}
      onDragStart={(e) => e.preventDefault()}
    >
       <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: `radial-gradient(circle, white 1px, transparent 1px)`, backgroundSize: `${40 * transform.scale}px ${40 * transform.scale}px`, backgroundPosition: `${transform.x}px ${transform.y}px` }}></div>
       <div ref={canvasRef} className="relative w-full h-full" style={{ transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`, transformOrigin: '0 0' }}>
           <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible" style={{ zIndex: 0 }}>
             {renderedLines.map(line => (
               <g key={line.id}>
                 <path d={line.path} fill="none" stroke="currentColor" strokeWidth="4" className="text-indigo-500/10" />
                 <path d={line.path} fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-500/40 transition-all pointer-events-auto" style={{ animation: 'dash 20s linear infinite' }} strokeDasharray="5 5" />
               </g>
             ))}
             {activeWire && (
               <path 
                 d={`M ${(activeWire.startPos.x - (containerRef.current?.getBoundingClientRect().left || 0) - transform.x) / transform.scale} ${(activeWire.startPos.y - (containerRef.current?.getBoundingClientRect().top || 0) - transform.y) / transform.scale} C ${(activeWire.startPos.x - (containerRef.current?.getBoundingClientRect().left || 0) - transform.x) / transform.scale + 100} ${(activeWire.startPos.y - (containerRef.current?.getBoundingClientRect().top || 0) - transform.y) / transform.scale}, ${(mousePos.x - (containerRef.current?.getBoundingClientRect().left || 0) - transform.x) / transform.scale - 100} ${(mousePos.y - (containerRef.current?.getBoundingClientRect().top || 0) - transform.y) / transform.scale}, ${(mousePos.x - (containerRef.current?.getBoundingClientRect().left || 0) - transform.x) / transform.scale} ${(mousePos.y - (containerRef.current?.getBoundingClientRect().top || 0) - transform.y) / transform.scale}`} 
                 fill="none" 
                 stroke="#6366f1" 
                 strokeWidth="2" 
                 strokeDasharray="5 5" 
                 className="pointer-events-none"
               />
             )}
           </svg>
           <div className="relative z-10 w-full h-full pointer-events-none">
             {Object.keys(workflow).map(id => {
               const isLoraNode = workflow[id].class_type.toLowerCase().includes('lora');
               const pos = nodeCoords[id] || { x: 0, y: 0 };
               const isReachable = reachableNodes.has(id);
               const hasSelection = selections.some(s => s.nodeId === id);
               const hasOrphanedSelection = hasSelection && !isReachable;

               return (
                 <div 
                    key={id} 
                    id={`node-${id}`} 
                    onMouseEnter={() => activeWire && handleWireDrop(id)}
                    style={{ 
                      position: 'absolute', 
                      left: pos.x, 
                      top: pos.y,
                      zIndex: draggingNode?.nodeId === id ? 100 : 10
                    }}
                    className={`w-72 bg-[#111114]/80 backdrop-blur-md border rounded-3xl shadow-2xl overflow-visible transition-all pointer-events-auto group ${activeWire && activeWire.nodeId !== id ? 'ring-4 ring-indigo-500/50 scale-[1.02] cursor-pointer' : 'border-white/5 hover:border-indigo-500/50'} ${draggingNode?.nodeId === id ? 'shadow-indigo-500/20' : ''} ${!isReachable ? 'opacity-40 grayscale-[0.5] hover:opacity-80' : ''} ${hasOrphanedSelection ? 'ring-2 ring-rose-500/50 shadow-[0_0_20px_rgba(244,63,94,0.1)]' : ''}`}
                    title={!isReachable ? "This node is unreachable and will be pruned during execution." : ""}
                  >
                   {hasOrphanedSelection && (
                      <div className="absolute -top-3 -right-3 bg-rose-500 text-white p-1.5 rounded-full z-50 animate-bounce shadow-lg shadow-rose-500/50" title="Orphaned Selection: This node is disconnected!">
                        <Trash2 className="w-4 h-4" />
                      </div>
                    )}
                   {/* Output Handle Section (Right Side) */}
                   <div className="absolute -right-3 top-[65px] flex flex-col gap-[18px] pointer-events-none">
                      {(objectInfo?.[workflow[id].class_type]?.output || ["OUTPUT"]).map((outName: string, idx: number) => (
                         <div 
                            key={idx} 
                            className="w-6 h-6 flex items-center justify-center group/output pointer-events-auto cursor-crosshair"
                            onMouseDown={(e) => handleOutputWireStart(id, idx, e)}
                            data-output-node={id}
                            data-output-index={idx}
                            title={outName}
                         >
                            <div className="w-3 h-3 bg-indigo-500 rounded-full border-2 border-[#111114] shadow-[0_0_10px_rgba(99,102,241,0.5)] group-hover/output:scale-150 transition-transform" />
                            <div className="absolute inset-0 bg-indigo-500/20 rounded-full animate-ping opacity-0 group-hover/output:opacity-100" />
                         </div>
                      ))}
                   </div>

                    <div 
                       onMouseDown={(e) => handleNodeDragStart(id, e)}
                       className="bg-white/5 p-4 border-b border-white/5 flex items-center justify-between cursor-move"
                    >
                      <div className="flex flex-col">
                        {workflow[id]._meta?.title && (
                          <span className="text-xs font-black text-white mb-0.5">{workflow[id]._meta.title}</span>
                        )}
                        <div className="flex items-center gap-2">
                          <span className="text-[8px] font-black text-indigo-400 uppercase tracking-widest opacity-80">{workflow[id].class_type}</span>
                          <span className="text-[7px] text-slate-600 font-mono">#{id}</span>
                        </div>
                      </div>
                    </div>
                       
                       <div className="p-4 space-y-4">
                         {Object.entries(workflow[id].inputs).map(([key, val]) => {
                           const isLink = Array.isArray(val);
                           return (
                             <div key={key} className="relative">
                                {/* Input Handle (Socket) - Connection Point */}
                                <div 
                                  className="absolute -left-7 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center group/input z-30 cursor-crosshair"
                                  onMouseDown={(e) => handleWireStart(id, key, e)}
                                  data-input-node={id}
                                  data-input-field={key}
                                >
                                  <div 
                                    className={`w-3 h-3 rounded-full border-2 border-[#111114] transition-all group-hover/input:scale-150 ${isLink ? 'bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]' : 'bg-slate-700'}`} 
                                  />
                                  {activeWire && activeWire.nodeId !== id && (
                                    <div className="absolute inset-0 bg-indigo-500/20 rounded-full animate-pulse" />
                                  )}
                                </div>

                                <div className="flex items-center justify-between gap-3 group/field">
                                  <div className="flex flex-col">
                                    <label className="text-[10px] font-bold text-slate-400 group-hover/field:text-indigo-400 transition-colors uppercase tracking-tight">{key}</label>
                                    <span className="text-[8px] text-slate-600 font-medium truncate max-w-[140px]">
                                      {isLink ? `Link: Node #${val[0]}` : String(val)}
                                    </span>
                                  </div>
                                  
                                  <button 
                                    onClick={() => toggleInput(id, key, workflow[id].class_type)}
                                    className={`p-2 rounded-xl transition-all ${selections.find(s => s.nodeId === id && s.field === key) ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'bg-white/5 text-slate-600 hover:text-slate-400'}`}
                                  >
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                             </div>
                           );
                         })}
                       </div>
                      
                      {isLoraNode && (
                        <div className="p-4 border-b border-white/5 bg-indigo-500/5 space-y-4">
                          <div className="flex items-center justify-between">
                            <label className="text-[9px] uppercase font-bold text-indigo-400 flex items-center gap-1.5">
                              <Layers className="w-3 h-3" />
                              LoRA Mapping
                            </label>
                            
                            <div className="flex bg-black/40 p-0.5 rounded-lg border border-white/5">
                              <button 
                                onClick={() => updateLoraSelection(id, { mode: 'list' })}
                                className={`text-[8px] px-2 py-1 rounded-md font-bold transition-all ${((typeof loraSelections[id] === 'string' ? 'list' : loraSelections[id]?.mode) || 'list') === 'list' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:text-slate-300'}`}
                              >
                                LIST
                              </button>
                              <button 
                                onClick={() => updateLoraSelection(id, { mode: 'static' })}
                                className={`text-[8px] px-2 py-1 rounded-md font-bold transition-all ${((typeof loraSelections[id] === 'string' ? 'list' : loraSelections[id]?.mode) || 'list') === 'static' ? 'bg-amber-500 text-black' : 'text-slate-500 hover:text-slate-300'}`}
                              >
                                STATIC
                              </button>
                            </div>
                          </div>

                          {((typeof loraSelections[id] === 'string' ? 'list' : loraSelections[id]?.mode) || 'list') === 'list' ? (
                            <div className="space-y-1.5">
                              <label className="text-[8px] text-slate-500 font-bold uppercase tracking-tighter">Dynamic Picker List</label>
                              <select 
                                value={typeof loraSelections[id] === 'string' ? loraSelections[id] : loraSelections[id]?.list || ''}
                                onChange={(e) => updateLoraSelection(id, { list: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-lg text-xs p-2 text-slate-300 outline-none focus:border-indigo-500/50"
                              >
                                <option value="">None (Default)</option>
                                {loraFiles.map(lf => (
                                  <option key={lf.name} value={lf.name}>{lf.name}</option>
                                ))}
                              </select>
                            </div>
                          ) : (
                            <div className="p-2 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                              <p className="text-[9px] text-amber-500 leading-tight">
                                <b>Static Mode</b>: The LoRA set in the workflow node will be used. No picker will appear in Discord.
                              </p>
                            </div>
                          )}
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

                              {/* Input Type Selector — shown when marked as Discord input */}
                              {isSelected && (
                                <div className="mb-2 p-2 rounded-xl bg-black/40 border border-indigo-500/20 space-y-1.5">
                                  {/* ComfyUI raw type info row */}
                                  <div className="flex items-center justify-between">
                                    <span className="text-[7px] font-bold text-slate-500 uppercase tracking-widest">ComfyUI type</span>
                                    <span className="text-[7px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">
                                      {(() => {
                                        const ni = objectInfo?.[workflow[id].class_type];
                                        const ii = ni?.input?.required?.[key] || ni?.input?.optional?.[key];
                                        if (!ii) return 'unknown';
                                        if (Array.isArray(ii[0])) return `ENUM (${ii[0].length} options)`;
                                        if (typeof ii[0] === 'string') return ii[0];
                                        return 'unknown';
                                      })()}
                                    </span>
                                  </div>
                                  {/* Discord Input Type label + badge */}
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
                                  </div>
                                  <select
                                    value={isSelected.type || 'text'}
                                    onChange={(e) => updateSelection(selections.indexOf(isSelected), { type: e.target.value })}
                                    onMouseDown={(e) => e.stopPropagation()}
                                    className="w-full bg-black/60 border border-indigo-500/30 rounded-lg text-[10px] px-2 py-1.5 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                                  >
                                    <option value="text">text — free text / prompt (modal)</option>
                                    <option value="image_upload">image_upload — image file (channel)</option>
                                    <option value="audio_upload">audio_upload — audio file (channel)</option>
                                    <option value="video_upload">video_upload — video file (channel)</option>
                                    <option value="select">select — dropdown choices (modal)</option>
                                  </select>
                                </div>
                              )}

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
        </div>
        <div className="absolute bottom-6 right-6 flex flex-col gap-2 z-20">
          <button onClick={resetView} className="bg-[#1c1c21] border border-white/10 p-3 rounded-xl text-slate-400 hover:text-white hover:border-indigo-500/50 transition-all shadow-2xl"><Maximize2 className="w-4 h-4" /></button>
          <div className="bg-[#1c1c21] border border-white/10 px-3 py-1.5 rounded-xl text-[10px] font-mono text-slate-500 flex items-center justify-center shadow-2xl">{Math.round(transform.scale * 100)}%</div>
        </div>
        <style jsx>{` @keyframes dash { to { stroke-dashoffset: -10; } } `}</style>
     </div>
  );
}
