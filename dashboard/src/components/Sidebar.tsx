"use client";

import React from 'react';
import { Network, Layout, Puzzle, Layers } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function Sidebar() {
  const { activeTab, setActiveTab } = useDashboard();

  return (
    <div className="w-60 bg-[#0d0d0f] border-r border-white/5 flex flex-col p-6 z-20 shadow-2xl relative">
      <div className="flex items-center gap-4 mb-10 px-2">
        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-fuchsia-500 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 rotate-3 transition-transform">
          <Network className="text-white w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-black tracking-tighter text-white">LINK</h1>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Dashboard</p>
        </div>
      </div>

      <nav className="space-y-2 mb-auto">
        <button onClick={() => setActiveTab('setup')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'setup' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
          <Layout className="w-4 h-4" />
          <span className="text-sm font-medium">Mission Control</span>
        </button>
        <button onClick={() => setActiveTab('architect')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'architect' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
          <Puzzle className="w-4 h-4" />
          <span className="text-sm font-medium">Architect View</span>
        </button>
        <button onClick={() => setActiveTab('modal-studio')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'modal-studio' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
          <div className="w-4 h-4 rounded border-2 border-current flex items-center justify-center text-[8px] font-bold">M</div>
          <span className="text-sm font-medium">Modal Studio</span>
        </button>
        <button onClick={() => setActiveTab('lora-studio')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'lora-studio' ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
          <Layers className="w-4 h-4" />
          <span className="text-sm font-medium">LoRA Studio</span>
        </button>
      </nav>
    </div>
  );
}
