"use client";

import React from 'react';
import { Network, Puzzle } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function MissionControl() {
  const { config, workflows, loraFiles } = useDashboard();

  return (
    <div className="max-w-4xl space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="p-8 rounded-3xl bg-gradient-to-br from-indigo-500/10 to-fuchsia-500/10 border border-white/5 relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[100px] -mr-32 -mt-32" />
        <h2 className="text-3xl font-black text-white mb-2 tracking-tight">Mission Control</h2>
        <p className="text-slate-400 leading-relaxed max-w-xl">Configure your ComfyUI integration and manage system-wide settings.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-500/20 flex items-center justify-center text-indigo-400"><Network className="w-5 h-5" /></div>
            <h3 className="font-bold text-white">ComfyUI Integration</h3>
          </div>
          <div className="space-y-4">
            <div className="grid gap-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Backend URL</label>
              <div className="flex gap-2">
                <input type="text" value={config.COMFY_URL || 'http://127.0.0.1:8188'} readOnly className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-indigo-300 focus:border-indigo-500/50 outline-none transition-all" />
                <button className="bg-white/5 hover:bg-white/10 text-slate-400 px-4 rounded-xl text-xs font-bold transition-all border border-white/5">Check Status</button>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/20">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-medium text-emerald-400">ComfyUI Backend Connected</span>
            </div>
          </div>
        </div>

        <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-fuchsia-500/20 flex items-center justify-center text-fuchsia-400"><Puzzle className="w-5 h-5" /></div>
            <h3 className="font-bold text-white">System Diagnostics</h3>
          </div>
          <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-xs text-slate-400 font-medium">Workflows Loaded</span>
                <span className="text-xs text-white font-bold">{workflows.length}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-xs text-slate-400 font-medium">LoRA Lists</span>
                <span className="text-xs text-white font-bold">{loraFiles.length}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-xs text-slate-400 font-medium">Discord Pipeline</span>
                <span className="text-xs text-emerald-400 font-bold">READY</span>
              </div>
          </div>
        </div>
      </div>
    </div>
  );
}
