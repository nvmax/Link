import React, { useState, useEffect } from 'react';
import { Package, GitBranch, ArrowRight, RefreshCw, Check, AlertTriangle, ExternalLink } from 'lucide-react';

// Small local registry of known-unregistered nodes so we can pre-fill URLs
// for the user. These nodes won't be in ComfyUI-Manager's custom-node-list.json.
const KNOWN_UNREGISTERED: Record<string, string> = {
  TextEncoderKrea2:    'https://github.com/ethanfel/ComfyUI-Krea2TextEncoder',
  Krea2SystemPrompt:   'https://github.com/ethanfel/ComfyUI-Krea2TextEncoder',
  AutoMegapixelReducer:'https://github.com/nvmax/aspect-ratio-resizer',
};

interface MissingNodesModalProps {
  missingNodes: string[];
  /** Nodes the backend couldn't resolve — triggers Phase 2 repo-input UI */
  unknownNodes?: string[];
  onInstall: (nodeRepos?: Record<string, string>) => Promise<void>;
  onImportAnyway: () => void;
  onCancel: () => void;
  isInstalling: boolean;
}

export function MissingNodesModal({
  missingNodes,
  unknownNodes = [],
  onInstall,
  onImportAnyway,
  onCancel,
  isInstalling,
}: MissingNodesModalProps) {
  const needsRepos = unknownNodes.length > 0;

  // Per-node repo URLs for Phase 2
  const [nodeRepos, setNodeRepos] = useState<Record<string, string>>({});

  // Pre-fill known URLs whenever unknownNodes changes
  useEffect(() => {
    if (unknownNodes.length === 0) return;
    setNodeRepos(prev => {
      const next = { ...prev };
      for (const cls of unknownNodes) {
        if (!next[cls]) {
          next[cls] = KNOWN_UNREGISTERED[cls] ?? '';
        }
      }
      return next;
    });
  }, [unknownNodes]);

  const allFilled = unknownNodes.every(cls => (nodeRepos[cls] ?? '').trim().length > 0);

  const handlePhase2Install = () => {
    const repos: Record<string, string> = {};
    for (const cls of unknownNodes) {
      const url = (nodeRepos[cls] ?? '').trim();
      if (url) repos[cls] = url;
    }
    onInstall(repos);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md animate-in fade-in duration-300 p-4 sm:p-6">
      <div className="bg-[#0d0d0f] border border-white/10 rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl text-left animate-in zoom-in-95 duration-300 max-h-[90vh] flex flex-col relative overflow-hidden">
        {/* Glow */}
        <div className="absolute top-0 left-0 w-64 h-64 bg-indigo-500/10 blur-[100px] -ml-32 -mt-32 pointer-events-none" />

        {/* Icon + title */}
        <div className="flex-shrink-0 mb-5">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-5 border ${
            needsRepos
              ? 'bg-amber-500/20 border-amber-500/30'
              : 'bg-indigo-500/20 border-indigo-500/30'
          }`}>
            {needsRepos
              ? <GitBranch className="w-6 h-6 text-amber-400" />
              : <Package className="w-6 h-6 text-indigo-400" />
            }
          </div>

          <h2 className="text-2xl font-black text-white mb-1">
            {needsRepos ? 'Provide Node Sources' : 'Missing Nodes Found'}
          </h2>
          <p className="text-slate-400 text-sm leading-relaxed">
            {needsRepos
              ? 'These nodes are not in ComfyUI-Manager\'s registry. Paste the GitHub repo URL for each one below — we\'ll install them directly from source.'
              : 'This workflow requires custom nodes that are not currently installed in your ComfyUI instance. Would you like to auto-install them now?'
            }
          </p>
        </div>

        {/* ── Phase 1: simple list ── */}
        {!needsRepos && (
          <div className="flex-1 overflow-y-auto min-h-0 mb-6">
            <div className="bg-black/40 border border-white/5 rounded-2xl p-4">
              <div className="text-[10px] uppercase font-bold text-slate-500 mb-3 tracking-widest">
                Required Classes
              </div>
              <div className="space-y-1.5">
                {missingNodes.filter(Boolean).map((node, i) => (
                  <div key={`${node}-${i}`} className="flex items-center gap-2 text-indigo-400 font-mono text-xs">
                    <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full shrink-0" />
                    {node}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Phase 2: repo input per unknown node ── */}
        {needsRepos && (
          <div className="flex-1 overflow-y-auto min-h-0 mb-6 space-y-3 pr-1 custom-scrollbar">
            {/* Auto-resolvable nodes (not in unknownNodes) */}
            {missingNodes.filter(n => !unknownNodes.includes(n)).length > 0 && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-3">
                <div className="text-[10px] uppercase font-bold text-emerald-500 mb-2 tracking-widest flex items-center gap-1.5">
                  <Check className="w-3 h-3" /> Auto-resolved
                </div>
                {missingNodes.filter(n => !unknownNodes.includes(n)).map((node, i) => (
                  <div key={i} className="text-emerald-400/80 font-mono text-xs mb-1 last:mb-0">
                    {node}
                  </div>
                ))}
              </div>
            )}

            {/* Unknown nodes needing a URL */}
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-3">
              <div className="text-[10px] uppercase font-bold text-amber-500 mb-3 tracking-widest flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3" /> Needs GitHub URL
              </div>
              <div className="space-y-3">
                {unknownNodes.map(cls => (
                  <div key={cls}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-amber-400 font-mono text-xs font-bold">{cls}</span>
                      {KNOWN_UNREGISTERED[cls] && (
                        <a
                          href={KNOWN_UNREGISTERED[cls]}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] text-amber-500/70 hover:text-amber-400 flex items-center gap-0.5 transition-colors"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span>Suggested</span>
                        </a>
                      )}
                    </div>
                    <input
                      type="url"
                      placeholder="https://github.com/author/repo"
                      value={nodeRepos[cls] ?? ''}
                      onChange={e =>
                        setNodeRepos(prev => ({ ...prev, [cls]: e.target.value }))
                      }
                      disabled={isInstalling}
                      className="w-full bg-black/50 border border-amber-500/20 focus:border-amber-500/50 rounded-xl px-3 py-2 text-xs font-mono text-slate-300 outline-none placeholder:text-slate-600 disabled:opacity-50 transition-colors"
                    />
                  </div>
                ))}
              </div>
            </div>

            <p className="text-[11px] text-slate-500 leading-relaxed px-1">
              Pre-filled URLs are based on our known-good registry. You can edit them or find the correct repo on
              {' '}<a href="https://github.com/search?q=ComfyUI&type=repositories" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 underline-offset-2 underline">GitHub</a>.
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-3 flex-shrink-0">
          {/* Primary button */}
          <button
            onClick={needsRepos ? handlePhase2Install : () => onInstall()}
            disabled={isInstalling || (needsRepos && !allFilled)}
            className={`group relative w-full py-4 font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 ${
              needsRepos
                ? 'bg-amber-600 hover:bg-amber-500 shadow-amber-500/20 text-black disabled:bg-white/5 disabled:text-slate-500'
                : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/20 text-white disabled:bg-slate-800 disabled:text-slate-500'
            }`}
          >
            {isInstalling ? (
              <>
                <RefreshCw className="animate-spin h-5 w-5" />
                Installing...
              </>
            ) : needsRepos ? (
              <>
                <GitBranch className="w-5 h-5" />
                Install from GitHub
              </>
            ) : (
              <>
                Install &amp; Fix Workflow
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>

          {needsRepos && !allFilled && (
            <p className="text-center text-[11px] text-amber-500/70">
              Fill in all GitHub URLs above to continue.
            </p>
          )}

          {/* Secondary buttons */}
          <div className="flex gap-3">
            <button
              onClick={onImportAnyway}
              disabled={isInstalling}
              className="flex-1 py-3 bg-white/5 hover:bg-white/10 disabled:opacity-50 text-slate-300 text-sm font-bold rounded-xl transition-all border border-white/5"
            >
              Import Anyway
            </button>
            <button
              onClick={onCancel}
              disabled={isInstalling}
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
