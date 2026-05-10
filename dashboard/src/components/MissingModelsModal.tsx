import React, { useState, useEffect } from 'react';
import { Database, Download, Check, AlertCircle, RefreshCw, FolderSearch, ExternalLink } from 'lucide-react';

export type ModelRepoInfo = {
  repo_id: string;
  hf_path?: string;
  gated?: boolean;
};

export const KNOWN_MODEL_REPOS: Record<string, ModelRepoInfo> = {
  'flux1-dev.safetensors':        { repo_id: 'black-forest-labs/FLUX.1-dev', gated: true },
  'ae.safetensors':               { repo_id: 'black-forest-labs/FLUX.1-dev', gated: true },
  't5xxl_fp16.safetensors':       { repo_id: 'comfyanonymous/flux_text_encoders', gated: false },
  'clip_l.safetensors':           { repo_id: 'comfyanonymous/flux_text_encoders', gated: false },
};

interface MissingModelsModalProps {
  missingModels: any[];
  onDownload: (modelsWithRepos: any[]) => void;
  onImportAnyway: () => void;
  onCancel: () => void;
  isDownloading: boolean;
  downloadProgress: Record<string, string>;
  onRetrySingle?: (model: any) => void;
}

export function MissingModelsModal({ 
  missingModels, 
  onDownload, 
  onImportAnyway, 
  onCancel,
  isDownloading,
  downloadProgress,
  onRetrySingle
}: MissingModelsModalProps) {
  const [modelRepos, setModelRepos] = useState<Record<string, string>>({});
  const [manualChecks, setManualChecks] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const initialRepos: Record<string, string> = {};
    missingModels.forEach(m => {
      if (KNOWN_MODEL_REPOS[m.filename]) {
        initialRepos[m.filename] = KNOWN_MODEL_REPOS[m.filename].repo_id;
      } else {
        initialRepos[m.filename] = '';
      }
    });
    setModelRepos(initialRepos);
  }, [missingModels]);

  const handleDownloadClick = () => {
    const payload = missingModels.map(m => ({
      ...m,
      repo_id: modelRepos[m.filename] || '',
      hf_path: KNOWN_MODEL_REPOS[m.filename]?.hf_path || m.filename,
      manuallyResolved: manualChecks[m.filename] || false
    }));
    onDownload(payload);
  };

  const handleRetry = (m: any) => {
    if (onRetrySingle) {
      onRetrySingle({
        ...m,
        repo_id: modelRepos[m.filename] || '',
        hf_path: KNOWN_MODEL_REPOS[m.filename]?.hf_path || m.filename,
        manuallyResolved: false
      });
    }
  };

  // Check if we can proceed with download
  const canDownload = missingModels.every(m => {
    const state = downloadProgress[m.filename];
    if (state === 'done') return true;
    if (manualChecks[m.filename]) return true;
    return !!modelRepos[m.filename];
  });

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md animate-in fade-in duration-300">
      <div className="bg-[#0d0d0f] border border-white/10 rounded-3xl p-8 max-w-2xl w-full shadow-2xl text-left scale-in-center animate-in zoom-in-95 duration-300 max-h-[90vh] flex flex-col relative overflow-hidden">
        {/* Glow effect matching MissionControl amber theme */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 blur-[100px] -mr-32 -mt-32 pointer-events-none" />

        <div className="flex-shrink-0">
          <div className="w-12 h-12 bg-amber-500/20 rounded-xl flex items-center justify-center mb-6 border border-amber-500/30">
            <Database className="w-6 h-6 text-amber-400" />
          </div>
          
          <h2 className="text-2xl font-black text-white mb-2">Missing Model Files</h2>
          <p className="text-slate-400 mb-6 text-sm leading-relaxed">
            This workflow requires model files that are not present in your ComfyUI models folder. 
            Provide a HuggingFace repository to auto-download them, or download them manually.
          </p>
        </div>
        
        <div className="flex-1 overflow-y-auto min-h-0 pr-2 custom-scrollbar space-y-4 mb-6">
          {missingModels.map(model => {
            const status = downloadProgress[model.filename];
            const isManualMode = !modelRepos[model.filename];
            const isGated = status === 'gated' || KNOWN_MODEL_REPOS[model.filename]?.gated;

            return (
              <div key={model.filename} className={`bg-white/5 border rounded-2xl p-4 transition-all ${
                status === 'done' ? 'border-emerald-500/30 bg-emerald-500/5' :
                status === 'error' ? 'border-rose-500/30 bg-rose-500/5' :
                status === 'gated' ? 'border-amber-500/50 bg-amber-500/10' :
                manualChecks[model.filename] ? 'border-indigo-500/30 bg-indigo-500/5' :
                'border-white/10'
              }`}>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-amber-400 font-mono text-sm font-bold">{model.filename}</span>
                      <span className="px-2 py-0.5 rounded-md bg-white/10 text-[10px] uppercase font-bold tracking-widest text-slate-400">
                        {model.folder}
                      </span>
                    </div>
                  </div>
                  
                  {/* Status Badge */}
                  {status && (
                    <div className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 ${
                      status === 'done' ? 'bg-emerald-500/20 text-emerald-400' :
                      status === 'downloading' ? 'bg-blue-500/20 text-blue-400 animate-pulse' :
                      status === 'error' ? 'bg-rose-500/20 text-rose-400' :
                      status === 'gated' ? 'bg-amber-500/20 text-amber-400' :
                      'bg-slate-500/20 text-slate-400'
                    }`}>
                      {status === 'downloading' && <RefreshCw className="w-3 h-3 animate-spin" />}
                      {status === 'done' && <Check className="w-3 h-3" />}
                      {status === 'error' && <AlertCircle className="w-3 h-3" />}
                      {status}
                    </div>
                  )}
                  {manualChecks[model.filename] && !status && (
                    <div className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-indigo-500/20 text-indigo-400 flex items-center gap-1.5">
                      <Check className="w-3 h-3" /> Manually Placed
                    </div>
                  )}
                </div>

                {/* Input Area */}
                {status !== 'done' && !manualChecks[model.filename] && (
                  <div className="space-y-3">
                    <div className="relative">
                      <input
                        type="text"
                        placeholder="HuggingFace Repo ID (e.g., black-forest-labs/FLUX.1-dev)"
                        value={modelRepos[model.filename] || ''}
                        onChange={(e) => setModelRepos(prev => ({ ...prev, [model.filename]: e.target.value }))}
                        disabled={isDownloading || status === 'gated'}
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-sm font-mono text-slate-300 focus:border-amber-500/50 outline-none transition-all placeholder:text-slate-600 disabled:opacity-50"
                      />
                    </div>

                    {/* Mode B: Manual Instructions */}
                    {isManualMode && (
                      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
                        <div className="flex items-start gap-2">
                          <FolderSearch className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                          <div className="space-y-2 flex-1">
                            <p className="text-xs text-amber-200/80 leading-relaxed">
                              This model has no known HuggingFace source. Download it manually and place it in your ComfyUI folder:
                            </p>
                            <code className="block bg-black/50 text-[10px] text-amber-400 font-mono p-2 rounded-lg break-all select-all">
                              {'<ComfyUI_Path>/models/' + model.folder + '/'}
                            </code>
                            <label className="flex items-center gap-2 mt-2 cursor-pointer group w-fit">
                              <div className="relative flex items-center justify-center">
                                <input 
                                  type="checkbox" 
                                  className="peer sr-only"
                                  checked={manualChecks[model.filename] || false}
                                  onChange={(e) => setManualChecks(prev => ({ ...prev, [model.filename]: e.target.checked }))}
                                  disabled={isDownloading}
                                />
                                <div className="w-4 h-4 rounded border border-amber-500/30 bg-black/40 peer-checked:bg-amber-500 peer-checked:border-amber-500 transition-all flex items-center justify-center">
                                  <Check className="w-3 h-3 text-black opacity-0 peer-checked:opacity-100 transition-opacity" strokeWidth={4} />
                                </div>
                              </div>
                              <span className="text-xs text-amber-200/60 group-hover:text-amber-200 transition-colors select-none font-medium">I've placed the file manually</span>
                            </label>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Mode C: Gated Model */}
                    {status === 'gated' && (
                      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 flex flex-col gap-3">
                        <p className="text-xs text-amber-200/90 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
                          This model requires license acceptance on HuggingFace.
                        </p>
                        <div className="flex gap-2">
                          <a 
                            href={`https://huggingface.co/${modelRepos[model.filename]}`} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="bg-amber-500 hover:bg-amber-400 text-black px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2"
                          >
                            Accept License <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                          {onRetrySingle && (
                            <button
                              onClick={() => handleRetry(model)}
                              disabled={isDownloading}
                              className="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${isDownloading ? 'animate-spin' : ''}`} />
                              Retry
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        <div className="flex flex-col gap-3 shrink-0 pt-2 border-t border-white/5">
          <button 
            onClick={handleDownloadClick}
            disabled={isDownloading || !canDownload}
            className="group relative w-full py-4 bg-amber-600 hover:bg-amber-500 disabled:bg-white/5 disabled:text-slate-500 text-black font-black rounded-xl transition-all shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2"
          >
            {isDownloading ? (
              <>
                <RefreshCw className="animate-spin h-5 w-5" />
                Downloading Models...
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                <span>Download Missing Models</span>
              </>
            )}
          </button>
          
          <div className="flex gap-3">
            <button 
              onClick={onImportAnyway}
              disabled={isDownloading}
              className="flex-1 py-3 bg-white/5 hover:bg-white/10 disabled:opacity-50 text-slate-300 text-sm font-bold rounded-xl transition-all border border-white/5"
            >
              Import Anyway
            </button>
            <button 
              onClick={onCancel}
              disabled={isDownloading}
              className="px-6 py-3 border border-white/5 hover:bg-white/10 disabled:opacity-50 text-slate-400 text-sm font-bold rounded-xl transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
