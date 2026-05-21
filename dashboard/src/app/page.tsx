"use client";

import React from 'react';
import { CheckCircle2, Menu } from 'lucide-react';
import { DashboardProvider, useDashboard } from '@/components/DashboardProvider';
import { Sidebar } from '@/components/Sidebar';
import { MissionControl } from '@/components/MissionControl';
import { ArchitectView } from '@/components/ArchitectView';
import { ModalStudio } from '@/components/ModalStudio';
import { LoraStudio } from '@/components/LoraStudio';
import { AiStudio } from '@/components/AiStudio';
import { RoleStudio } from '@/components/RoleStudio';
import { MissingNodesModal } from '@/components/MissingNodesModal';
import { MissingModelsModal } from '@/components/MissingModelsModal';
import { ThemeStudioModal } from '@/components/ThemeStudioModal';

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
    pendingLoad,
    setPendingLoad,
    importWorkflow,
    missingModels,
    setMissingModels,
    isDownloadingModels,
    modelDownloadProgress,
    modelDownloadStats,
    handleModelDownload,
    handleRetrySingleModel,
    isSidebarOpen,
    setIsSidebarOpen,
    toggleSidebar,
    isConfigLoaded
  } = useDashboard();

  if (!isConfigLoaded) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0a0a0c] text-white">
        <div className="relative flex items-center justify-center mb-8">
          {/* Animated glow background */}
          <div className="absolute w-24 h-24 bg-indigo-500/20 rounded-full blur-xl animate-pulse" />
          <div className="absolute w-36 h-36 bg-fuchsia-500/10 rounded-full blur-2xl animate-pulse delay-75" />
          
          {/* Main loader */}
          <div className="w-16 h-16 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
        </div>
        <div className="text-center space-y-2">
          <h1 className="text-lg font-black tracking-wider uppercase bg-gradient-to-r from-indigo-400 to-fuchsia-400 bg-clip-text text-transparent animate-pulse">
            nvmax / Link
          </h1>
          <p className="text-xs text-slate-500 font-mono tracking-widest uppercase">
            Synchronizing Secure Core...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary font-sans overflow-hidden selection:bg-accent-glow">
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="h-20 border-b border-border-theme flex items-center justify-between px-4 lg:px-8 bg-bg-sidebar/50 backdrop-blur-xl z-10">
            <div className="flex items-center gap-4">
              <button 
                onClick={toggleSidebar}
                className="lg:hidden p-2 -ml-2 text-slate-400 hover:text-white transition-colors"
              >
                <Menu className="w-6 h-6" />
              </button>
              {activeTab !== 'setup' && (
                <>
                  <div className="hidden sm:block h-8 w-px bg-white/10 mx-2" />
                  <div className="flex flex-col">
                    <span className="text-[10px] sm:text-xs text-slate-500 font-bold uppercase tracking-wider">Active Workspace</span>
                    <span className="text-xs sm:text-sm font-medium text-white flex items-center gap-2 truncate max-w-[120px] sm:max-w-none">
                      {selectedWorkflow?.name || 'No Workflow Selected'}
                      {selectedWorkflow && <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />}
                    </span>
                  </div>
                </>
              )}
            </div>

            {activeTab !== 'setup' && (
              <div className="flex items-center gap-3">
                <button 
                  onClick={saveWorkflow} 
                  disabled={!selectedWorkflow}
                  className="flex items-center gap-2 bg-white text-black px-4 sm:px-6 py-2 sm:py-2.5 rounded-xl font-bold text-[10px] sm:text-sm hover:bg-indigo-500 hover:text-white transition-all shadow-xl active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                >
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span className="hidden xs:inline">Save Manifest</span>
                  <span className="xs:hidden">Save</span>
                </button>
              </div>
            )}
          </header>

          <main className="flex-1 overflow-y-auto p-4 sm:p-8">
            {activeTab === 'setup' && <MissionControl />}
            {activeTab === 'architect' && <ArchitectView />}
            {activeTab === 'modal-studio' && <ModalStudio />}
            {activeTab === 'lora-studio' && <LoraStudio />}
            {activeTab === 'ai-studio' && <AiStudio />}
            {activeTab === 'role-studio' && <RoleStudio />}
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
                setPendingLoad(false);
                if (!pendingLoad) {
                  // Only re-import if this was triggered from importWorkflow
                  await importWorkflow(name, workflow, true);
                }
              } else {
                setMissingNodes([]);
              }
            }}
            onCancel={() => {
              setMissingNodes([]);
              setPendingImport(null);
              setPendingLoad(false);
            }}
            isInstalling={isInstalling}
          />
        )}

        {missingModels.length > 0 && (
          <MissingModelsModal 
            missingModels={missingModels}
            onDownload={handleModelDownload}
            onImportAnyway={async () => {
              if (pendingImport && !pendingLoad) {
                // Only re-import if this was triggered from importWorkflow
                const { name, workflow } = pendingImport;
                setMissingModels([]);
                setPendingImport(null);
                setPendingLoad(false);
                await importWorkflow(name, workflow, true);
              } else {
                // Triggered from loadWorkflow — workflow already displayed, just dismiss
                setMissingModels([]);
                setPendingImport(null);
                setPendingLoad(false);
              }
            }}
            onCancel={() => {
              setMissingModels([]);
              setPendingImport(null);
              setPendingLoad(false);
            }}
            isDownloading={isDownloadingModels}
            downloadProgress={modelDownloadProgress}
            downloadStats={modelDownloadStats}
            onRetrySingle={handleRetrySingleModel}
          />
        )}
        {isSidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden animate-in fade-in duration-300"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
        <ThemeStudioModal />
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
