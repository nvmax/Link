"use client";

import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { DashboardProvider, useDashboard } from '@/components/DashboardProvider';
import { Sidebar } from '@/components/Sidebar';
import { MissionControl } from '@/components/MissionControl';
import { ArchitectView } from '@/components/ArchitectView';
import { ModalStudio } from '@/components/ModalStudio';
import { LoraStudio } from '@/components/LoraStudio';
import { MissingNodesModal } from '@/components/MissingNodesModal';

function DashboardContent() {
  const { 
    activeTab, 
    selectedWorkflow, 
    saveWorkflow,
    missingNodes,
    setMissingNodes,
    handleNodeInstall,
    isInstalling,
    pendingImport,
    setPendingImport,
    importWorkflow
  } = useDashboard();

  return (
    <div className="flex h-screen bg-[#0a0a0c] text-slate-200 font-sans overflow-hidden selection:bg-indigo-500/30">
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="h-20 border-b border-white/5 flex items-center justify-between px-8 bg-[#0d0d0f]/50 backdrop-blur-xl z-10">
            <div className="flex items-center gap-4">
              <div className="h-8 w-px bg-white/10 mx-2" />
              <div className="flex flex-col">
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Active Workspace</span>
                <span className="text-sm font-medium text-white flex items-center gap-2">
                  {selectedWorkflow?.name || 'No Workflow Selected'}
                  {selectedWorkflow && <CheckCircle2 className="w-3 h-3 text-emerald-500" />}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button 
                onClick={saveWorkflow} 
                disabled={!selectedWorkflow}
                className="flex items-center gap-2 bg-white text-black px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-indigo-500 hover:text-white transition-all shadow-xl active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <CheckCircle2 className="w-4 h-4" />
                Save Manifest
              </button>
            </div>
          </header>

          <main className="flex-1 overflow-y-auto p-8">
            {activeTab === 'setup' && <MissionControl />}
            {activeTab === 'architect' && <ArchitectView />}
            {activeTab === 'modal-studio' && <ModalStudio />}
            {activeTab === 'lora-studio' && <LoraStudio />}
          </main>
        </div>

        {missingNodes.length > 0 && (
          <MissingNodesModal 
            missingNodes={missingNodes}
            onInstall={handleNodeInstall}
            onImportAnyway={async () => {
              if (pendingImport) {
                const { name, workflow } = pendingImport;
                setMissingNodes([]);
                setPendingImport(null);
                await importWorkflow(name, workflow, true);
              }
            }}
            onCancel={() => {
              setMissingNodes([]);
              setPendingImport(null);
            }}
            isInstalling={isInstalling}
          />
        )}
      </div>
    </div>
  );
}

export default function LinkDashboard() {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
}
