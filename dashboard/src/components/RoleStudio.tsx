"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Shield, 
  ShieldAlert, 
  ShieldCheck, 
  RefreshCw, 
  Save, 
  Check, 
  X, 
  Search, 
  ChevronRight, 
  Server, 
  Users, 
  ArrowRight,
  HelpCircle,
  AlertCircle
} from 'lucide-react';
import { useDashboard } from './DashboardProvider';

interface DiscordRole {
  id: string;
  name: string;
  color: string | null;
  is_everyone: boolean;
  position: number;
}

interface DiscordGuild {
  id: string;
  name: string;
  icon: string | null;
  roles: DiscordRole[];
}

interface PermissionMapping {
  guild_permissions: Record<string, Record<string, string[]>>;
}

export function RoleStudio() {
  const { workflows, showToast } = useDashboard();

  // API states
  const [guilds, setGuilds] = useState<DiscordGuild[]>([]);
  const [permissions, setPermissions] = useState<Record<string, Record<string, string[]>>>({});
  const [status, setStatus] = useState<'loading' | 'online' | 'offline' | 'error'>('loading');
  const [isSaving, setIsSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // UI Selection states
  const [selectedGuildId, setSelectedGuildId] = useState<string | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);

  // Search filter for workflows
  const [workflowSearch, setWorkflowSearch] = useState('');

  // Fetch guilds & existing permissions mappings
  const fetchData = useCallback(async (showNotification = false) => {
    setStatus('loading');
    try {
      // 1. Fetch connected guilds and roles from FastAPI running on port 8001
      const guildsRes = await fetch('http://127.0.0.1:8001/api/discord/guilds');
      if (!guildsRes.ok) {
        throw new Error(`Guilds fetch failed: ${guildsRes.statusText}`);
      }
      const guildsData = await guildsRes.json();
      
      if (guildsData.status === 'offline') {
        setStatus('offline');
        return;
      } else if (guildsData.status === 'loading') {
        setStatus('loading');
        // Retry in 2 seconds if bot is still loading guilds
        setTimeout(() => fetchData(false), 2000);
        return;
      }
      
      setGuilds(guildsData.guilds || []);
      
      // Select first guild by default if none selected
      if (guildsData.guilds && guildsData.guilds.length > 0 && !selectedGuildId) {
        setSelectedGuildId(guildsData.guilds[0].id);
      }

      // 2. Fetch permission mappings
      const permRes = await fetch('http://127.0.0.1:8001/api/discord/permissions');
      if (permRes.ok) {
        const permData: PermissionMapping = await permRes.json();
        setPermissions(permData.guild_permissions || {});
      }

      setStatus('online');
      if (showNotification) {
        showToast('Successfully fetched latest Discord roles & permissions!', 'success');
      }
    } catch (err) {
      console.error('Error fetching Role Studio data:', err);
      setStatus('error');
      showToast('Failed to connect to the Discord API server.', 'error');
    }
  }, [selectedGuildId, showToast]);

  useEffect(() => {
    fetchData();
  }, []);

  // Find currently selected guild
  const selectedGuild = useMemo(() => {
    return guilds.find(g => g.id === selectedGuildId) || null;
  }, [guilds, selectedGuildId]);

  // When guild changes, reset selected role
  useEffect(() => {
    if (selectedGuild) {
      // Select the first role or @everyone if available
      const everyoneRole = selectedGuild.roles.find(r => r.is_everyone);
      const defaultRole = everyoneRole || selectedGuild.roles[0] || null;
      setSelectedRoleId(defaultRole ? defaultRole.id : null);
    } else {
      setSelectedRoleId(null);
    }
  }, [selectedGuildId]);

  // Find currently selected role
  const selectedRole = useMemo(() => {
    if (!selectedGuild) return null;
    return selectedGuild.roles.find(r => r.id === selectedRoleId) || null;
  }, [selectedGuild, selectedRoleId]);

  // Get allowed workflows list for current guild & role
  const selectedRoleAllowedWorkflows = useMemo(() => {
    if (!selectedGuildId || !selectedRoleId) return [];
    return permissions[selectedGuildId]?.[selectedRoleId] || [];
  }, [permissions, selectedGuildId, selectedRoleId]);

  // Toggle permission for a single workflow
  const handleToggleWorkflow = (wfName: string) => {
    if (!selectedGuildId || !selectedRoleId) return;

    setPermissions(prev => {
      const nextPermissions = { ...prev };
      const nextRoles = { ...(nextPermissions[selectedGuildId] || {}) };
      
      const currentAllowed = nextRoles[selectedRoleId] || [];
      let nextAllowed: string[];

      if (currentAllowed.includes(wfName)) {
        nextAllowed = currentAllowed.filter(name => name !== wfName);
      } else {
        nextAllowed = [...currentAllowed, wfName];
      }

      nextRoles[selectedRoleId] = nextAllowed;
      nextPermissions[selectedGuildId] = nextRoles;
      return nextPermissions;
    });
  };

  // Allow or Deny all workflows for the current role
  const handleToggleAllWorkflows = (allowAll: boolean) => {
    if (!selectedGuildId || !selectedRoleId) return;

    setPermissions(prev => {
      const nextPermissions = { ...prev };
      const nextRoles = { ...(nextPermissions[selectedGuildId] || {}) };

      if (allowAll) {
        // Add all workflows
        nextRoles[selectedRoleId] = workflows.map(wf => wf.name);
      } else {
        // Clear all workflows
        nextRoles[selectedRoleId] = [];
      }

      nextPermissions[selectedGuildId] = nextRoles;
      return nextPermissions;
    });
  };

  // Check if a workflow is configured on ANY role in this guild (to show restriction indicator)
  const isWorkflowRestrictedInGuild = useCallback((wfName: string) => {
    if (!selectedGuildId) return false;
    const guildRules = permissions[selectedGuildId] || {};
    return Object.values(guildRules).some(allowedList => allowedList.includes(wfName));
  }, [permissions, selectedGuildId]);

  // Save updated permissions mapping back to disk
  const handleSavePermissions = async () => {
    setIsSaving(true);
    try {
      const res = await fetch('http://127.0.0.1:8001/api/discord/permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ guild_permissions: permissions })
      });

      if (!res.ok) {
        throw new Error('Save failed');
      }

      showToast('Permissions configuration updated successfully!', 'success');
    } catch (err) {
      console.error('Error saving permissions:', err);
      showToast('Failed to save permissions configuration.', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  // Filtered workflows based on search query
  const filteredWorkflows = useMemo(() => {
    return workflows.filter(wf => {
      const nameMatch = wf.name.toLowerCase().includes(workflowSearch.toLowerCase());
      const commandMatch = (wf.manifest?.discord_command || '').toLowerCase().includes(workflowSearch.toLowerCase());
      const descMatch = (wf.manifest?.description || '').toLowerCase().includes(workflowSearch.toLowerCase());
      return nameMatch || commandMatch || descMatch;
    });
  }, [workflows, workflowSearch]);

  // Count active restrictions in the current server
  const restrictedWorkflowsCount = useMemo(() => {
    if (!selectedGuildId) return 0;
    const guildRules = permissions[selectedGuildId] || {};
    const uniqueRestricted = new Set<string>();
    Object.values(guildRules).forEach(allowedList => {
      allowedList.forEach(wf => uniqueRestricted.add(wf));
    });
    return uniqueRestricted.size;
  }, [permissions, selectedGuildId]);

  return (
    <div className="flex flex-col gap-6 h-full animate-in fade-in slide-in-from-bottom-4 duration-500 pb-16">
      
      {/* Header Panel */}
      <div className="flex flex-col md:flex-row md:items-center justify-between bg-bg-sidebar/40 backdrop-blur-md p-6 rounded-3xl border border-white/5 shadow-2xl gap-4">
        <div className="flex items-center gap-5">
          <div className="w-14 h-14 bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 rounded-2xl flex items-center justify-center shadow-xl shadow-indigo-500/10">
            <Shield className="text-white w-7 h-7" />
          </div>
          <div>
            <h2 className="text-2xl font-black text-white tracking-tight">Role Studio</h2>
            <p className="text-slate-400 text-xs font-semibold mt-0.5">Define who can invoke specific ComfyUI workflows inside Discord server roles.</p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button 
            onClick={() => fetchData(true)}
            disabled={status === 'loading' || isSaving}
            className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-all border border-white/5 active:scale-95 disabled:opacity-50"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${status === 'loading' ? 'animate-spin' : ''}`} />
          </button>
          
          <button 
            onClick={handleSavePermissions}
            disabled={status !== 'online' || isSaving}
            className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white px-5 py-3 rounded-xl font-bold text-sm transition-all shadow-lg shadow-indigo-500/15 border border-indigo-400/20 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            <span>{isSaving ? 'Saving Changes...' : 'Save Settings'}</span>
          </button>
        </div>
      </div>

      {/* Connection Offline/Failure Fallbacks */}
      {status === 'loading' && guilds.length === 0 && (
        <div className="bg-bg-sidebar/20 rounded-3xl border border-white/5 p-20 flex flex-col items-center justify-center gap-4 text-center">
          <RefreshCw className="w-10 h-10 text-indigo-500 animate-spin" />
          <h3 className="text-lg font-bold text-white uppercase tracking-wider">Syncing Role Studio...</h3>
          <p className="text-slate-500 text-xs max-w-sm">Contacting the running Discord client. Restructuring command structures and role hierarchies...</p>
        </div>
      )}

      {status === 'offline' && (
        <div className="bg-bg-sidebar/30 rounded-3xl border border-white/5 p-16 flex flex-col items-center justify-center gap-4 text-center max-w-2xl mx-auto my-10 shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-extrabold text-white">Discord Bot is Offline</h3>
          <p className="text-slate-400 text-xs leading-relaxed">
            Role Studio fetches your connected Discord servers and roles <span className="text-indigo-400 font-bold">directly from the running Discord bot instance</span>. 
            Currently, the bot is not running or hasn't connected successfully.
          </p>
          <div className="p-4 bg-white/5 rounded-2xl text-[11px] text-slate-500 leading-relaxed max-w-md mt-2 text-left space-y-1">
            <p className="font-bold text-slate-300">How to resolve:</p>
            <p>1. Make sure your bot is launched (`python main.py`).</p>
            <p>2. Verify that your `DISCORD_TOKEN` in Mission Control is valid.</p>
            <p>3. Check that you have added your target server IDs to the Whitelist in Mission Control.</p>
          </div>
          <button 
            onClick={() => fetchData(true)}
            className="mt-4 bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-bold text-xs transition-all active:scale-95 shadow-md shadow-indigo-500/20"
          >
            Retry Connection
          </button>
        </div>
      )}

      {status === 'error' && guilds.length === 0 && (
        <div className="bg-bg-sidebar/30 rounded-3xl border border-white/5 p-16 flex flex-col items-center justify-center gap-4 text-center max-w-2xl mx-auto my-10">
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-extrabold text-white">Connection Error</h3>
          <p className="text-slate-400 text-xs">
            We failed to reach the FastAPI endpoint on port <code className="bg-white/5 px-1.5 py-0.5 rounded text-rose-400 font-mono">8001</code>.
            Please ensure that your Python backend API is running properly.
          </p>
          <button 
            onClick={() => fetchData(true)}
            className="mt-2 bg-indigo-500 hover:bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-bold text-xs transition-all active:scale-95"
          >
            Retry Now
          </button>
        </div>
      )}

      {/* Active Studio Grid */}
      {guilds.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 items-stretch">
          
          {/* COLUMN 1: Servers List */}
          <div className="xl:col-span-1 bg-[#0d0d0f]/90 border border-white/5 rounded-3xl p-5 shadow-2xl flex flex-col h-[650px]">
            <div className="flex items-center gap-2 mb-4 shrink-0 px-1">
              <Server className="w-4 h-4 text-indigo-400" />
              <h3 className="font-bold text-white text-sm uppercase tracking-wider">Discord Servers</h3>
            </div>
            
            <div className="space-y-2 overflow-y-auto flex-1 pr-1 custom-scrollbar">
              {guilds.map((guild) => {
                const isSelected = guild.id === selectedGuildId;
                const rulesCount = Object.values(permissions[guild.id] || {}).flat().length;

                return (
                  <button
                    key={guild.id}
                    onClick={() => setSelectedGuildId(guild.id)}
                    className={`w-full text-left p-3.5 rounded-2xl border transition-all flex items-center justify-between group active:scale-[0.98] ${
                      isSelected 
                        ? 'bg-indigo-500/10 border-indigo-500/30 text-white shadow-lg' 
                        : 'bg-white/[0.02] border-white/5 text-slate-400 hover:border-white/15 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {guild.icon ? (
                        <img 
                          src={guild.icon} 
                          alt={guild.name} 
                          className="w-8 h-8 rounded-xl object-cover shadow"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-xs font-black">
                          {guild.name.charAt(0)}
                        </div>
                      )}
                      <div className="flex flex-col min-w-0">
                        <span className={`text-xs font-bold truncate leading-none mb-1 ${isSelected ? 'text-white' : 'text-slate-200 group-hover:text-white'}`}>
                          {guild.name}
                        </span>
                        <span className="text-[9px] text-slate-500 font-mono truncate">{guild.id}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {rulesCount > 0 && (
                        <span className="text-[9px] font-black bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                          {rulesCount}
                        </span>
                      )}
                      <ChevronRight className={`w-3.5 h-3.5 text-slate-500 transition-transform ${isSelected ? 'translate-x-0.5 text-indigo-400' : 'group-hover:translate-x-0.5 group-hover:text-slate-350'}`} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* COLUMN 2: Server Roles Hierarchy */}
          <div className="xl:col-span-1 bg-[#0d0d0f]/90 border border-white/5 rounded-3xl p-5 shadow-2xl flex flex-col h-[650px]">
            <div className="flex items-center justify-between mb-4 shrink-0 px-1">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-400" />
                <h3 className="font-bold text-white text-sm uppercase tracking-wider">Roles Hierarchy</h3>
              </div>
              <span className="text-[9px] text-slate-500 font-bold bg-white/5 px-2 py-0.5 rounded-full">
                {selectedGuild?.roles.length || 0} Total
              </span>
            </div>

            {selectedGuild && (
              <div className="space-y-2 overflow-y-auto flex-1 pr-1 custom-scrollbar">
                {selectedGuild.roles.map((role) => {
                  const isSelected = role.id === selectedRoleId;
                  const allowedCount = permissions[selectedGuild.id]?.[role.id]?.length || 0;
                  
                  // Color conversion logic
                  const pillColor = role.color || '#94a3b8';

                  return (
                    <button
                      key={role.id}
                      onClick={() => setSelectedRoleId(role.id)}
                      className={`w-full text-left p-3.5 rounded-2xl border transition-all flex items-center justify-between group active:scale-[0.98] ${
                        isSelected 
                          ? 'bg-indigo-500/10 border-indigo-500/30 text-white shadow-lg' 
                          : 'bg-white/[0.02] border-white/5 text-slate-400 hover:border-white/15 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {/* Role Color Pill Indicator */}
                        <div 
                          className="w-3.5 h-3.5 rounded-full border border-white/10 shrink-0" 
                          style={{ backgroundColor: pillColor }}
                        />
                        <div className="flex flex-col min-w-0">
                          <span className={`text-xs font-bold truncate leading-none mb-1 ${isSelected ? 'text-white' : 'text-slate-200 group-hover:text-white'}`}>
                            {role.name}
                          </span>
                          <span className="text-[9px] text-slate-500 font-mono truncate">
                            {role.is_everyone ? 'Default @everyone role' : `ID: ${role.id}`}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {allowedCount > 0 && (
                          <span className="text-[9px] font-black bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                            {allowedCount} Allowed
                          </span>
                        )}
                        <ChevronRight className={`w-3.5 h-3.5 text-slate-500 transition-transform ${isSelected ? 'translate-x-0.5 text-indigo-400' : 'group-hover:translate-x-0.5 group-hover:text-slate-350'}`} />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {!selectedGuild && (
              <div className="flex-1 flex items-center justify-center text-slate-500 text-xs italic text-center p-4">
                Select a server to view roles
              </div>
            )}
          </div>

          {/* COLUMN 3 & 4: Allowed Workflows Panel */}
          <div className="xl:col-span-2 bg-[#0d0d0f]/90 border border-white/5 rounded-3xl p-6 shadow-2xl flex flex-col h-[650px] relative">
            
            {selectedRole && selectedGuild && (
              <>
                {/* Header Information for Selected Role */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-white/5 pb-4 mb-4 gap-3 shrink-0">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <div 
                        className="w-4 h-4 rounded-full border border-white/10" 
                        style={{ backgroundColor: selectedRole.color || '#94a3b8' }}
                      />
                      <h4 className="font-extrabold text-white text-lg">{selectedRole.name} Permissions</h4>
                    </div>
                    <p className="text-[11px] text-slate-500 font-medium mt-1 leading-relaxed">
                      {selectedRole.is_everyone ? (
                        <>Public access settings. Workflows selected here are accessible to <span className="text-indigo-400 font-bold">everyone</span> by default.</>
                      ) : (
                        <>Assign permitted generation workflows for members possessing the role.</>
                      )}
                    </p>
                  </div>

                  {/* Quick toggle actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleAllWorkflows(true)}
                      className="text-[9px] font-black uppercase text-indigo-400 hover:text-indigo-300 bg-indigo-500/5 hover:bg-indigo-500/10 border border-indigo-500/15 px-2.5 py-1.5 rounded-xl transition-all"
                    >
                      Allow All
                    </button>
                    <button
                      onClick={() => handleToggleAllWorkflows(false)}
                      className="text-[9px] font-black uppercase text-slate-500 hover:text-slate-400 bg-white/5 hover:bg-white/10 border border-white/5 px-2.5 py-1.5 rounded-xl transition-all"
                    >
                      Revoke All
                    </button>
                  </div>
                </div>

                {/* Info Box about Fallbacks */}
                <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-2xl p-4 mb-4 shrink-0 flex items-start gap-3">
                  <HelpCircle className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                  <div className="text-[11px] text-slate-400 leading-relaxed font-semibold">
                    <span className="text-white font-extrabold block mb-0.5">Standard Pipeline Fallback Rules</span>
                    If a workflow is <span className="text-indigo-300">not assigned to any roles</span> on this server, it remains <span className="text-emerald-400">publicly available</span>. 
                    The moment you restrict a workflow to specific roles, it becomes blocked for unauthorized users.
                  </div>
                </div>

                {/* Workflows Search bar */}
                <div className="relative mb-4 shrink-0">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Filter workflows by name or command..."
                    value={workflowSearch}
                    onChange={(e) => setWorkflowSearch(e.target.value)}
                    className="w-full bg-black/40 border border-white/5 rounded-xl pl-11 pr-4 py-3 text-xs text-white placeholder:text-slate-600 focus:border-indigo-500/50 outline-none transition-all"
                  />
                  {workflowSearch && (
                    <button 
                      onClick={() => setWorkflowSearch('')}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Scrollable Workflows checkboxes grid */}
                <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 custom-scrollbar pb-2">
                  {filteredWorkflows.length === 0 ? (
                    <div className="py-12 flex flex-col items-center justify-center opacity-40 gap-2">
                      <AlertCircle className="w-7 h-7 text-slate-600" />
                      <span className="text-xs font-bold uppercase tracking-widest text-slate-500">No matching workflows</span>
                    </div>
                  ) : (
                    filteredWorkflows.map((wf) => {
                      const isAllowed = selectedRoleAllowedWorkflows.includes(wf.name);
                      
                      // Check if restricted in guild
                      const isRestricted = isWorkflowRestrictedInGuild(wf.name);
                      
                      const discordCmd = wf.manifest?.discord_command || wf.name;
                      const description = wf.manifest?.description || `Trigger ComfyUI execution command for ${wf.name}`;

                      return (
                        <div
                          key={wf.name}
                          onClick={() => handleToggleWorkflow(wf.name)}
                          className={`group flex items-center justify-between p-4 rounded-2xl border transition-all cursor-pointer select-none active:scale-[0.99] ${
                            isAllowed
                              ? 'bg-indigo-500/10 border-indigo-500/30'
                              : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05] hover:border-white/10'
                          }`}
                        >
                          <div className="flex items-center gap-3.5 min-w-0">
                            {/* Checkbox indicator */}
                            <div className={`w-5 h-5 rounded-lg border flex items-center justify-center transition-all ${
                              isAllowed 
                                ? 'bg-indigo-500 border-indigo-400 text-white shadow-[0_0_8px_rgba(99,102,241,0.3)]' 
                                : 'border-white/10 group-hover:border-white/25 bg-black/20'
                            }`}>
                              {isAllowed && <Check className="w-3.5 h-3.5 stroke-[3px]" />}
                            </div>

                            <div className="flex flex-col min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={`text-xs font-bold leading-none ${isAllowed ? 'text-indigo-300' : 'text-slate-200'}`}>
                                  {wf.name}
                                </span>
                                <span className="text-[9px] font-mono text-slate-500 bg-white/5 border border-white/5 px-1.5 py-0.5 rounded">
                                  /{discordCmd.toLowerCase()}
                                </span>
                              </div>
                              <span className="text-[10px] text-slate-500 truncate mt-1 leading-none">
                                {description}
                              </span>
                            </div>
                          </div>

                          <div className="shrink-0 ml-2">
                            {isAllowed ? (
                              <span className="text-[9px] font-black uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                                Allowed
                              </span>
                            ) : isRestricted ? (
                              <span className="text-[9px] font-black uppercase bg-amber-500/10 text-amber-500 border border-amber-500/20 px-2 py-0.5 rounded-full" title="Restricted to other specific roles. Members without those roles cannot access this.">
                                Restricted
                              </span>
                            ) : (
                              <span className="text-[9px] font-black uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full animate-pulse-slow" title="Publicly accessible to everyone on the server.">
                                Public
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Footer Metrics Panel */}
                <div className="shrink-0 border-t border-white/5 pt-4 mt-2 flex items-center justify-between text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{selectedRoleAllowedWorkflows.length} assigned to this role</span>
                  </span>
                  <span>{restrictedWorkflowsCount} restricted in server</span>
                </div>
              </>
            )}

            {(!selectedRole || !selectedGuild) && (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-3 text-center p-8 animate-in fade-in duration-300">
                <Shield className="w-12 h-12 text-slate-700 animate-pulse" />
                <div>
                  <h4 className="font-bold text-slate-400 text-sm">No Role Selected</h4>
                  <p className="text-[11px] text-slate-500 mt-1 max-w-xs">Select a whitelisted server and role to begin mapping permissions.</p>
                </div>
              </div>
            )}
          </div>
          
        </div>
      )}

    </div>
  );
}
