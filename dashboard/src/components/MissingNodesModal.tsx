import React from 'react';

interface MissingNodesModalProps {
  missingNodes: string[];
  onInstall: () => void;
  onImportAnyway: () => void;
  onCancel: () => void;
  isInstalling: boolean;
}

export function MissingNodesModal({ 
  missingNodes, 
  onInstall, 
  onImportAnyway, 
  onCancel,
  isInstalling 
}: MissingNodesModalProps) {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md animate-in fade-in duration-300 p-4 sm:p-6">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-8 max-w-md w-full shadow-2xl text-left scale-in-center animate-in zoom-in-95 duration-300">
        <div className="w-12 h-12 bg-indigo-500/20 rounded-xl flex items-center justify-center mb-6 border border-indigo-500/30">
          <svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </div>
        
        <h2 className="text-2xl font-black text-white mb-2">Missing Nodes Found</h2>
        <p className="text-slate-400 mb-6 text-sm leading-relaxed">
          This workflow requires custom nodes that are not currently installed in your ComfyUI instance. Would you like to auto-install them now?
        </p>
        
        <div className="bg-slate-950 rounded-xl p-4 mb-8 max-h-48 overflow-y-auto border border-slate-800 scrollbar-thin scrollbar-thumb-slate-800">
          <div className="text-[10px] uppercase font-bold text-slate-500 mb-2 tracking-widest">Required Classes:</div>
          {missingNodes.filter(Boolean).map((node, index) => (
            <div key={`${node}-${index}`} className="text-indigo-400 font-mono text-xs mb-1 last:mb-0 flex items-center gap-2">
              <span className="w-1 h-1 bg-indigo-500 rounded-full"></span>
              {node}
            </div>
          ))}
        </div>
        
        <div className="flex flex-col gap-3">
          <button 
            onClick={onInstall}
            disabled={isInstalling}
            className="group relative w-full py-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white font-bold rounded-xl transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2"
          >
            {isInstalling ? (
              <>
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Installing...
              </>
            ) : (
              <>
                <span>Install & Fix Workflow</span>
                <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </>
            )}
          </button>
          
          <div className="flex gap-3">
            <button 
              onClick={onImportAnyway}
              disabled={isInstalling}
              className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 text-sm font-bold rounded-xl transition-all"
            >
              Import Anyway
            </button>
            <button 
              onClick={onCancel}
              disabled={isInstalling}
              className="px-6 py-3 border border-slate-800 hover:bg-slate-800 disabled:opacity-50 text-slate-400 text-sm font-bold rounded-xl transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
