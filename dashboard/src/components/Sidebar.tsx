"use client";

import { Network, Layout, Puzzle, Layers, X, Sparkles, Palette, Shield } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function Sidebar() {
  const { activeTab, setActiveTab, isSidebarOpen, setIsSidebarOpen, setIsThemeModalOpen } = useDashboard();

  const handleTabClick = (tab: any) => {
    setActiveTab(tab);
    setIsSidebarOpen(false);
  };

  return (
    <div className={`
      fixed lg:static inset-y-0 left-0 w-60 bg-bg-sidebar border-r border-border-theme 
      flex flex-col p-6 z-50 shadow-2xl transition-transform duration-300
      ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
    `}>
      <div className="flex items-center justify-between mb-10 px-2">
        <div className="flex items-center gap-4">
          <img 
            src="/icon.png" 
            alt="Link" 
            className="w-10 h-10 rounded-xl shadow-lg shadow-accent-glow rotate-3 transition-transform object-cover" 
          />
          <div>
            <h1 className="text-xl font-black tracking-tighter text-text-primary">LINK</h1>
            <p className="text-[10px] text-text-secondary font-bold uppercase tracking-widest">Dashboard</p>
          </div>
        </div>
        <button 
          onClick={() => setIsSidebarOpen(false)}
          className="lg:hidden p-2 text-text-secondary hover:text-text-primary"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <nav className="space-y-2 mb-auto">
        <button onClick={() => handleTabClick('setup')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'setup' ? 'bg-accent-primary text-white shadow-lg shadow-accent-glow' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'}`}>
          <Layout className="w-4 h-4" />
          <span className="text-sm font-medium">Mission Control</span>
        </button>
        <button onClick={() => handleTabClick('architect')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'architect' ? 'bg-accent-primary text-white shadow-lg shadow-accent-glow' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'}`}>
          <Puzzle className="w-4 h-4" />
          <span className="text-sm font-medium">Architect View</span>
        </button>
        <button onClick={() => handleTabClick('modal-studio')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'modal-studio' ? 'bg-accent-primary text-white shadow-lg shadow-accent-glow' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'}`}>
          <div className="w-4 h-4 rounded border-2 border-current flex items-center justify-center text-[8px] font-bold">M</div>
          <span className="text-sm font-medium">Modal Studio</span>
        </button>
        <button onClick={() => handleTabClick('lora-studio')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'lora-studio' ? 'bg-accent-primary text-white shadow-lg shadow-accent-glow' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'}`}>
          <Layers className="w-4 h-4" />
          <span className="text-sm font-medium">LoRA Studio</span>
        </button>
        <button onClick={() => handleTabClick('ai-studio')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'ai-studio' ? 'bg-accent-primary text-white shadow-lg shadow-accent-glow' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'}`}>
          <Sparkles className="w-4 h-4" />
          <span className="text-sm font-medium">AI Studio</span>
        </button>
        <button onClick={() => handleTabClick('role-studio')} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === 'role-studio' ? 'bg-accent-primary text-white shadow-lg shadow-accent-glow' : 'text-text-secondary hover:bg-bg-card hover:text-text-primary'}`}>
          <Shield className="w-4 h-4" />
          <span className="text-sm font-medium">Role Studio</span>
        </button>
      </nav>

      <div className="mt-auto pt-6 border-t border-border-theme">
        <button 
          onClick={() => setIsThemeModalOpen(true)}
          className="w-full flex items-center gap-3 p-3 rounded-xl transition-all text-text-secondary hover:bg-bg-card hover:text-text-primary group border border-dashed border-border-theme hover:border-accent-primary/40 active:scale-95"
        >
          <Palette className="w-4 h-4 text-text-secondary group-hover:text-accent-primary transition-colors" />
          <span className="text-sm font-medium">Theme Studio</span>
        </button>
      </div>
    </div>
  );
}
