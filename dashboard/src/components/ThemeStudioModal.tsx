"use client";

import React, { useState, useEffect } from 'react';
import { X, Check, Copy, Upload, Download, RefreshCw, Palette, Settings, Code, Share2 } from 'lucide-react';
import { useDashboard, THEME_PRESETS } from './DashboardProvider';

const COLOR_TOKENS = [
  { key: 'bg-primary', label: 'Primary Background', desc: 'Main window background color' },
  { key: 'bg-sidebar', label: 'Sidebar Background', desc: 'Left navigation background' },
  { key: 'bg-card', label: 'Card / Panel Background', desc: 'Studio cards and dialogs background' },
  { key: 'text-primary', label: 'Text Primary', desc: 'Core headers and active text' },
  { key: 'text-secondary', label: 'Text Secondary', desc: 'Muted text and descriptions' },
  { key: 'accent-primary', label: 'Accent Color', desc: 'Buttons, links, and active borders' },
  { key: 'accent-hover', label: 'Accent Hover', desc: 'Color when hovering accent elements' },
  { key: 'border-color', label: 'Border Color', desc: 'Grid lines and dividers (supports rgba)' },
  { key: 'accent-glow', label: 'Accent Glow', desc: 'Box shadows, selections, and glows' }
];

export function ThemeStudioModal() {
  const {
    activeTheme,
    setActiveTheme,
    customThemeColors,
    setCustomThemeColors,
    customCss,
    setCustomCss,
    isThemeModalOpen,
    setIsThemeModalOpen,
    showToast
  } = useDashboard();

  const [activeTab, setActiveTab] = useState<'presets' | 'custom' | 'css' | 'share'>('presets');
  const [importText, setImportText] = useState('');
  
  // Keep track of edited custom colors locally during modal edit, initialized from current active theme or custom colors
  const [localColors, setLocalColors] = useState<Record<string, string>>({});

  useEffect(() => {
    // If the theme is a preset, load its colors into our localColors state so they can edit it
    const currentColors = activeTheme === 'custom' 
      ? customThemeColors 
      : (THEME_PRESETS[activeTheme]?.colors || THEME_PRESETS['classic-dark'].colors);
    setLocalColors(currentColors);
  }, [activeTheme, customThemeColors, isThemeModalOpen]);

  if (!isThemeModalOpen) return null;

  const handleColorChange = (key: string, value: string) => {
    const updated = { ...localColors, [key]: value };
    setLocalColors(updated);
    setCustomThemeColors(updated);
    if (activeTheme !== 'custom') {
      setActiveTheme('custom');
      showToast('Theme switched to Custom to edit colors', 'info');
    }
  };

  const resetToDefault = () => {
    if (confirm('Are you sure you want to reset all themes to Classic Dark default?')) {
      setActiveTheme('classic-dark');
      setCustomThemeColors(THEME_PRESETS['classic-dark'].colors);
      setCustomCss('');
      showToast('Theme reset to defaults!', 'success');
    }
  };

  const handleExport = () => {
    const themeConfig = {
      theme: activeTheme,
      colors: activeTheme === 'custom' ? customThemeColors : THEME_PRESETS[activeTheme]?.colors,
      css: customCss
    };
    const jsonStr = JSON.stringify(themeConfig, null, 2);
    navigator.clipboard.writeText(jsonStr);
    showToast('Theme JSON copied to clipboard!', 'success');
  };

  const handleImport = () => {
    try {
      const parsed = JSON.parse(importText);
      if (parsed.colors) {
        setCustomThemeColors(parsed.colors);
        setLocalColors(parsed.colors);
      }
      if (typeof parsed.css === 'string') {
        setCustomCss(parsed.css);
      }
      if (parsed.theme) {
        setActiveTheme(parsed.theme);
      } else {
        setActiveTheme('custom');
      }
      setImportText('');
      showToast('Theme imported successfully!', 'success');
    } catch (e) {
      showToast('Invalid theme JSON format', 'error');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center z-[100] p-4 animate-in fade-in duration-200">
      <div className="bg-bg-sidebar border border-border-theme rounded-3xl w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col overflow-hidden text-text-primary animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-6 border-b border-border-theme flex justify-between items-center bg-bg-card/30">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-accent-primary/10 text-accent-primary shadow-inner">
              <Palette className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight">Theme Studio</h2>
              <p className="text-xs text-text-secondary">Customize colors, presets, and inject custom CSS</p>
            </div>
          </div>
          <button 
            onClick={() => setIsThemeModalOpen(false)}
            className="p-2 text-text-secondary hover:text-text-primary hover:bg-bg-card rounded-xl transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-border-theme bg-bg-card/10 px-6 gap-2">
          <button
            onClick={() => setActiveTab('presets')}
            className={`py-3 px-4 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'presets' 
                ? 'border-accent-primary text-accent-primary' 
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <Palette className="w-4 h-4" />
            Theme Presets
          </button>
          <button
            onClick={() => setActiveTab('custom')}
            className={`py-3 px-4 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'custom' 
                ? 'border-accent-primary text-accent-primary' 
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <Settings className="w-4 h-4" />
            Color Customizer
          </button>
          <button
            onClick={() => setActiveTab('css')}
            className={`py-3 px-4 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'css' 
                ? 'border-accent-primary text-accent-primary' 
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <Code className="w-4 h-4" />
            Custom CSS
          </button>
          <button
            onClick={() => setActiveTab('share')}
            className={`py-3 px-4 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'share' 
                ? 'border-accent-primary text-accent-primary' 
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <Share2 className="w-4 h-4" />
            Share & Sync
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 p-6 overflow-y-auto bg-bg-primary/20">
          
          {/* Tab 1: PRESETS */}
          {activeTab === 'presets' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                
                {/* Loop through presets */}
                {Object.entries(THEME_PRESETS).map(([key, item]) => {
                  const isActive = activeTheme === key;
                  return (
                    <button
                      key={key}
                      onClick={() => {
                        setActiveTheme(key);
                        showToast(`Applied ${item.name} theme`, 'success');
                      }}
                      className={`relative flex flex-col p-4 rounded-2xl border text-left transition-all hover:scale-[1.02] ${
                        isActive 
                          ? 'border-accent-primary bg-accent-primary/5 shadow-lg shadow-accent-primary/5' 
                          : 'border-border-theme bg-bg-card/45 hover:bg-bg-card hover:border-text-secondary/20'
                      }`}
                    >
                      <div className="flex justify-between items-center mb-3">
                        <span className="font-bold text-sm">{item.name}</span>
                        {isActive && (
                          <div className="w-5 h-5 rounded-full bg-accent-primary flex items-center justify-center text-white">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </div>
                        )}
                      </div>

                      {/* Small Swatch Preview */}
                      <div className="mt-auto flex flex-col gap-2 p-2 rounded-xl bg-black/25">
                        <div className="flex gap-1.5 justify-center">
                          <div className="w-5 h-5 rounded-full border border-white/10" style={{ backgroundColor: item.colors['bg-primary'] }} title="Primary BG" />
                          <div className="w-5 h-5 rounded-full border border-white/10" style={{ backgroundColor: item.colors['bg-sidebar'] }} title="Sidebar BG" />
                          <div className="w-5 h-5 rounded-full border border-white/10" style={{ backgroundColor: item.colors['bg-card'] }} title="Card BG" />
                          <div className="w-5 h-5 rounded-full border border-white/10" style={{ backgroundColor: item.colors['accent-primary'] }} title="Accent" />
                        </div>
                        <div className="flex justify-between text-[9px] text-white/50 px-1 font-mono">
                          <span>{item.colors['accent-primary'].substring(0, 7)}</span>
                          <span>{item.colors['bg-primary'].substring(0, 7)}</span>
                        </div>
                      </div>
                    </button>
                  );
                })}

                {/* Custom Preset Selection Option */}
                <button
                  onClick={() => {
                    setActiveTheme('custom');
                    showToast('Switched to Custom Theme mode', 'success');
                  }}
                  className={`flex flex-col p-4 rounded-2xl border text-left transition-all hover:scale-[1.02] ${
                    activeTheme === 'custom'
                      ? 'border-accent-primary bg-accent-primary/5 shadow-lg shadow-accent-primary/5'
                      : 'border-border-theme bg-bg-card/45 hover:bg-bg-card hover:border-text-secondary/20'
                  }`}
                >
                  <div className="flex justify-between items-center mb-3">
                    <span className="font-bold text-sm">Custom Colors</span>
                    {activeTheme === 'custom' && (
                      <div className="w-5 h-5 rounded-full bg-accent-primary flex items-center justify-center text-white">
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                      </div>
                    )}
                  </div>
                  <p className="text-[10px] text-text-secondary mb-4 leading-normal">Fully custom color specifications of your choice.</p>
                  <div className="mt-auto flex items-center justify-center gap-1.5 py-1.5 rounded-xl border border-dashed border-border-theme text-xs font-semibold text-accent-primary">
                    <Palette className="w-3.5 h-3.5" />
                    Configure Colors
                  </div>
                </button>

              </div>
            </div>
          )}

          {/* Tab 2: CUSTOM COLOR PICKER */}
          {activeTab === 'custom' && (
            <div className="space-y-4">
              <div className="bg-accent-primary/5 border border-accent-primary/20 rounded-2xl p-4 text-xs text-text-secondary flex justify-between items-center">
                <div>
                  <p className="font-semibold text-text-primary mb-0.5">Custom Mode Active</p>
                  <p>Editing any color below will automatically clone your active preset into a Custom Theme.</p>
                </div>
                {activeTheme !== 'custom' && (
                  <button
                    onClick={() => setActiveTheme('custom')}
                    className="px-3 py-1.5 bg-accent-primary text-white rounded-xl text-xs font-bold hover:bg-accent-hover transition-all"
                  >
                    Set to Custom Mode
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {COLOR_TOKENS.map((token) => {
                  const val = localColors[token.key] || '#ffffff';
                  return (
                    <div key={token.key} className="flex items-center justify-between p-3.5 rounded-2xl bg-bg-card/35 border border-border-theme">
                      <div className="flex-1 mr-4">
                        <label className="text-xs font-bold block text-text-primary mb-0.5">{token.label}</label>
                        <span className="text-[10px] text-text-secondary leading-normal block">{token.desc}</span>
                      </div>
                      
                      <div className="flex items-center gap-2 shrink-0">
                        {/* Text box of hex */}
                        <input
                          type="text"
                          value={val}
                          onChange={(e) => handleColorChange(token.key, e.target.value)}
                          className="w-20 bg-bg-primary/50 text-center font-mono text-[11px] py-1 border border-border-theme rounded-md text-text-primary"
                        />
                        {/* Native color picker button */}
                        <div className="w-8 h-8 rounded-lg border border-border-theme overflow-hidden relative shadow-inner cursor-pointer shrink-0">
                          <input
                            type="color"
                            value={val.startsWith('#') && val.length === 7 ? val : '#111111'}
                            onChange={(e) => handleColorChange(token.key, e.target.value)}
                            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                          />
                          <div className="w-full h-full" style={{ backgroundColor: val }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab 3: CUSTOM CSS */}
          {activeTab === 'css' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center text-xs">
                <span className="text-text-secondary">Inject arbitrary CSS styles dynamically</span>
                <span className="font-mono text-accent-primary">Live Injection Enabled</span>
              </div>

              <textarea
                value={customCss}
                onChange={(e) => setCustomCss(e.target.value)}
                placeholder="/* Add your custom CSS here */&#10;.Sidebar_button { border-radius: 9999px; }&#10;header { border-bottom: 2px solid var(--accent-primary) !important; }"
                rows={10}
                className="w-full font-mono text-xs p-4 bg-black/40 border border-border-theme rounded-2xl text-text-primary focus:outline-none focus:border-accent-primary resize-none placeholder:opacity-30"
              />

              <div className="bg-bg-card/40 border border-border-theme rounded-2xl p-4 text-xs">
                <h4 className="font-bold text-text-primary mb-2 flex items-center gap-1.5">
                  <Code className="w-4 h-4 text-accent-primary" />
                  Styling Cheat Sheet
                </h4>
                <ul className="space-y-1.5 text-text-secondary list-disc pl-4 font-mono text-[10px]">
                  <li>Backgrounds: <span className="text-text-primary">var(--bg-primary)</span>, <span className="text-text-primary">var(--bg-sidebar)</span>, <span className="text-text-primary">var(--bg-card)</span></li>
                  <li>Accents: <span className="text-text-primary">var(--accent-primary)</span>, <span className="text-text-primary">var(--accent-hover)</span></li>
                  <li>Texts: <span className="text-text-primary">var(--text-primary)</span>, <span className="text-text-primary">var(--text-secondary)</span></li>
                  <li>Borders: <span className="text-text-primary">var(--border-color)</span></li>
                </ul>
              </div>
            </div>
          )}

          {/* Tab 4: EXPORT/IMPORT */}
          {activeTab === 'share' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Export Side */}
                <div className="p-5 rounded-2xl bg-bg-card/35 border border-border-theme flex flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-bold flex items-center gap-2 mb-2">
                      <Download className="w-4 h-4 text-accent-primary" />
                      Export Theme
                    </h3>
                    <p className="text-xs text-text-secondary mb-4 leading-normal">Export your current active configuration including customizable colors and Custom CSS as a JSON string to share with others.</p>
                  </div>
                  <button
                    onClick={handleExport}
                    className="w-full py-2.5 bg-accent-primary/10 border border-accent-primary/20 text-accent-primary hover:bg-accent-primary hover:text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 active:scale-95"
                  >
                    <Copy className="w-4 h-4" />
                    Copy Theme JSON to Clipboard
                  </button>
                </div>

                {/* Import Side */}
                <div className="p-5 rounded-2xl bg-bg-card/35 border border-border-theme flex flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-bold flex items-center gap-2 mb-2">
                      <Upload className="w-4 h-4 text-accent-primary" />
                      Import Theme
                    </h3>
                    <p className="text-xs text-text-secondary mb-3 leading-normal">Paste a valid theme configuration JSON string below to import immediately.</p>
                    <textarea
                      value={importText}
                      onChange={(e) => setImportText(e.target.value)}
                      placeholder='{ "theme": "custom", "colors": { "bg-primary": "#0a0a0c", ... }, "css": "" }'
                      rows={4}
                      className="w-full font-mono text-[10px] p-3 bg-black/30 border border-border-theme rounded-xl text-text-primary focus:outline-none focus:border-accent-primary resize-none"
                    />
                  </div>
                  <button
                    disabled={!importText.trim()}
                    onClick={handleImport}
                    className="w-full py-2.5 mt-3 bg-accent-primary text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 active:scale-95"
                  >
                    <Upload className="w-4 h-4" />
                    Apply Pasted Theme
                  </button>
                </div>

              </div>
            </div>
          )}

        </div>

        {/* Footer actions */}
        <div className="p-4 border-t border-border-theme bg-bg-card/35 flex justify-between items-center">
          <button
            onClick={resetToDefault}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-all border border-transparent hover:border-rose-500/20 active:scale-95"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Reset Theme Defaults
          </button>
          
          <button
            onClick={() => setIsThemeModalOpen(false)}
            className="px-6 py-2.5 bg-accent-primary hover:bg-accent-hover text-white rounded-xl text-xs font-bold shadow-xl active:scale-95 transition-all"
          >
            Close Studio
          </button>
        </div>

      </div>
    </div>
  );
}
