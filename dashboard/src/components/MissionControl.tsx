"use client";

import React from 'react';
import { Network, Puzzle, Settings, Save, X } from 'lucide-react';
import { useDashboard } from './DashboardProvider';

export function MissionControl() {
  const { config, setConfig, saveConfig, workflows, loraFiles } = useDashboard();

  const handleConfigChange = (key: string, value: string) => {
    setConfig({ ...config, [key]: value });
  };

  const [newGuildId, setNewGuildId] = React.useState('');
  const [newChannelId, setNewChannelId] = React.useState('');

  const handleAddGuild = () => {
    const val = newGuildId.trim();
    if (val) {
      const current = config.ALLOWED_GUILD_ID || '';
      const ids = current.split(',').filter(Boolean);
      if (!ids.includes(val)) {
        const next = current ? `${current},${val}` : val;
        handleConfigChange('ALLOWED_GUILD_ID', next);
      }
      setNewGuildId('');
    }
  };

  const handleAddChannel = () => {
    const val = newChannelId.trim();
    if (val) {
      const current = config.ALLOWED_CHANNEL_ID || '';
      const ids = current.split(',').filter(Boolean);
      if (!ids.includes(val)) {
        const next = current ? `${current},${val}` : val;
        handleConfigChange('ALLOWED_CHANNEL_ID', next);
      }
      setNewChannelId('');
    }
  };

  return (
    <div className="max-w-4xl space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
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
                <input 
                  type="text" 
                  value={config.COMFY_URL || 'http://127.0.0.1:8188'} 
                  onChange={(e) => handleConfigChange('COMFY_URL', e.target.value)}
                  className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-indigo-300 focus:border-indigo-500/50 outline-none transition-all" 
                />
                <button className="bg-white/5 hover:bg-white/10 text-slate-400 px-4 rounded-xl text-xs font-bold transition-all border border-white/5 shrink-0">Check Status</button>
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
                <BotStatus />
              </div>
          </div>
        </div>
      </div>

      <div className="bg-[#0d0d0f] rounded-3xl border border-white/5 p-6 space-y-6 shadow-2xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center text-amber-400"><Settings className="w-5 h-5" /></div>
            <div>
              <h3 className="font-bold text-white">Environment Configuration</h3>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">Manage .env variables</p>
            </div>
          </div>
          <button 
            onClick={() => saveConfig(config)}
            className="bg-amber-500 text-black px-6 py-2.5 rounded-xl font-black text-sm hover:bg-amber-400 transition-all shadow-xl shadow-amber-500/20 flex items-center justify-center gap-2 active:scale-95 shrink-0"
          >
            <Save className="w-4 h-4" /> Save Settings
          </button>
        </div>

        <div className="space-y-8 pt-4 border-t border-white/5">
          {/* Discord Access Management */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Guild Management */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Whitelisted Servers</label>
                <span className="text-[10px] text-indigo-400 font-bold bg-indigo-500/10 px-2 py-0.5 rounded-full">{config.ALLOWED_GUILD_ID?.split(',').filter(Boolean).length || 0} Active</span>
              </div>
              
              <div className="space-y-3">
                {config.ALLOWED_GUILD_ID?.split(',').filter(Boolean).map((gid: string) => (
                  <GuildCard key={gid} id={gid} onRemove={(id) => {
                    const newIds = config.ALLOWED_GUILD_ID.split(',').filter((x: string) => x !== id).join(',');
                    handleConfigChange('ALLOWED_GUILD_ID', newIds);
                  }} />
                ))}
                
                  <div className="flex gap-2 p-2 bg-black/40 border border-white/5 rounded-2xl">
                    <input 
                      type="text"
                      placeholder="Enter Server ID..."
                      value={newGuildId}
                      onChange={(e) => setNewGuildId(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleAddGuild();
                        }
                      }}
                      className="flex-1 bg-transparent border-none px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600"
                    />
                    <button 
                      onClick={handleAddGuild}
                      className="bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 px-4 rounded-xl text-[10px] font-black uppercase transition-all"
                    >
                      Add
                    </button>
                  </div>
              </div>
            </div>

            {/* Channel Management */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Whitelisted Channels</label>
                <span className="text-[10px] text-fuchsia-400 font-bold bg-fuchsia-500/10 px-2 py-0.5 rounded-full">{config.ALLOWED_CHANNEL_ID?.split(',').filter(Boolean).length || 0} Active</span>
              </div>
              
              <div className="space-y-3">
                {config.ALLOWED_CHANNEL_ID?.split(',').filter(Boolean).map((cid: string) => (
                  <ChannelCard key={cid} id={cid} onRemove={(id) => {
                    const newIds = config.ALLOWED_CHANNEL_ID.split(',').filter((x: string) => x !== id).join(',');
                    handleConfigChange('ALLOWED_CHANNEL_ID', newIds);
                  }} />
                ))}
                
                  <div className="flex gap-2 p-2 bg-black/40 border border-white/5 rounded-2xl">
                    <input 
                      type="text"
                      placeholder="Enter Channel ID..."
                      value={newChannelId}
                      onChange={(e) => setNewChannelId(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleAddChannel();
                        }
                      }}
                      className="flex-1 bg-transparent border-none px-3 py-2 text-xs text-white outline-none placeholder:text-slate-600"
                    />
                    <button 
                      onClick={handleAddChannel}
                      className="bg-fuchsia-500/10 hover:bg-fuchsia-500/20 text-fuchsia-400 px-4 rounded-xl text-[10px] font-black uppercase transition-all"
                    >
                      Add
                    </button>
                  </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-8 border-t border-white/5">
            <div className="space-y-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Discord Token</label>
              <input 
                type="password" 
                value={config.DISCORD_TOKEN || ''} 
                onChange={(e) => handleConfigChange('DISCORD_TOKEN', e.target.value)}
                placeholder="MTQ5NjI0MzYz..."
                className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-slate-300 focus:border-amber-500/50 outline-none transition-all placeholder:text-white/10" 
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Database URL</label>
              <input 
                type="text" 
                value={config.DATABASE_URL || 'sqlite:///data/link.db'} 
                onChange={(e) => handleConfigChange('DATABASE_URL', e.target.value)}
                className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-sm font-mono text-slate-300 focus:border-amber-500/50 outline-none transition-all" 
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function BotStatus() {
  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    const check = () => {
      fetch('http://127.0.0.1:8001/health')
        .then(res => res.json())
        .then(data => setConnected(data.bot_connected))
        .catch(() => setConnected(false));
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${connected ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'}`}>
      {connected ? 'Ready' : 'Offline'}
    </span>
  );
}

function GuildCard({ id, onRemove }: { id: string, onRemove: (id: string) => void }) {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch(`http://127.0.0.1:8001/api/discord/guild/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        setData(null);
        setLoading(false);
      });
  }, [id]);

  return (
    <div className="group flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-2xl hover:border-indigo-500/30 transition-all">
      <div className="flex items-center gap-3">
        {data?.icon ? (
          <img src={data.icon} className="w-8 h-8 rounded-lg shadow-lg" alt="" />
        ) : (
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 font-black text-[10px]">
            {loading ? '...' : (data?.name?.charAt(0) || '?')}
          </div>
        )}
        <div className="flex flex-col">
          <span className="text-xs font-bold text-white leading-none mb-1">{loading ? 'Loading...' : (data?.name || 'Unknown Server')}</span>
          <span className="text-[9px] text-slate-500 font-mono tracking-tight">{id}</span>
        </div>
      </div>
      <button onClick={() => onRemove(id)} className="p-2 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-500 transition-all">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function ChannelCard({ id, onRemove }: { id: string, onRemove: (id: string) => void }) {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    fetch(`http://127.0.0.1:8001/api/discord/channel/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        setData(null);
        setLoading(false);
      });
  }, [id]);

  return (
    <div className="group flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-2xl hover:border-fuchsia-500/30 transition-all">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-fuchsia-500/10 flex items-center justify-center text-fuchsia-400 font-black text-[10px]">
          #
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-bold text-white leading-none mb-1">{loading ? 'Loading...' : (data?.name || 'Unknown Channel')}</span>
          <span className="text-[9px] text-slate-500 font-mono tracking-tight">{data?.guild_name || '...'} · {id}</span>
        </div>
      </div>
      <button onClick={() => onRemove(id)} className="p-2 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-500 transition-all">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
