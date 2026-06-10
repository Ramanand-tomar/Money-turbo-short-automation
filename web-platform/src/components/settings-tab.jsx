import React from 'react';
import { Database, Cpu, Info } from 'lucide-react';

export default function SettingsTab({ 
  configSettings, 
  setConfigSettings, 
  activeConfigStatus, 
  handleSaveSettings, 
  isSavingSettings 
}) {
  return (
    <div className="space-y-8 animate-fade-in">
      <header className="page-header">
        <h2 className="page-title text-2xl md:text-3xl font-extrabold">SaaS Platform Settings</h2>
        <p className="page-subtitle text-zinc-400 text-sm md:text-base">Configure external API integrations dynamically. Settings are persisted securely inside NeonDB.</p>
      </header>

      {/* Responsive layout: Grid stacks on smaller screens, row on desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* API Configuration Form */}
        <form onSubmit={handleSaveSettings} className="glass-panel p-6 md:p-8 lg:col-span-2 space-y-6 flex flex-col justify-between">
          <div className="space-y-6">
            <h3 className="text-base md:text-lg font-bold text-zinc-100 flex items-center gap-2">
              <Database size={20} className="text-yellow-400" />
              Database API Keys Configuration
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Google Gemini API Key</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.gemini_api_key} 
                  onChange={e => setConfigSettings({...configSettings, gemini_api_key: e.target.value})}
                  placeholder={activeConfigStatus.gemini_api_key_configured ? "••••••••••••••••" : "Enter Gemini API Key"}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Gemini Fallback API Key 2</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.gemini_api_key_2} 
                  onChange={e => setConfigSettings({...configSettings, gemini_api_key_2: e.target.value})}
                  placeholder={activeConfigStatus.gemini_api_key_2_configured ? "••••••••••••••••" : "Enter Gemini Fallback Key 2"}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Gemini Fallback API Key 3</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.gemini_api_key_3} 
                  onChange={e => setConfigSettings({...configSettings, gemini_api_key_3: e.target.value})}
                  placeholder={activeConfigStatus.gemini_api_key_3_configured ? "••••••••••••••••" : "Enter Gemini Fallback Key 3"}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Gemini Fallback API Key 4</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.gemini_api_key_4} 
                  onChange={e => setConfigSettings({...configSettings, gemini_api_key_4: e.target.value})}
                  placeholder={activeConfigStatus.gemini_api_key_4_configured ? "••••••••••••••••" : "Enter Gemini Fallback Key 4"}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Gemini Fallback API Key 5</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.gemini_api_key_5} 
                  onChange={e => setConfigSettings({...configSettings, gemini_api_key_5: e.target.value})}
                  placeholder={activeConfigStatus.gemini_api_key_5_configured ? "••••••••••••••••" : "Enter Gemini Fallback Key 5"}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Pexels Visuals API Key</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.pexels_api_key} 
                  onChange={e => setConfigSettings({...configSettings, pexels_api_key: e.target.value})}
                  placeholder={activeConfigStatus.pexels_api_key_configured ? "••••••••••••••••" : "Enter Pexels API Key"}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Azure Speech SDK Key</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.azure_speech_key} 
                  onChange={e => setConfigSettings({...configSettings, azure_speech_key: e.target.value})}
                  placeholder={activeConfigStatus.azure_speech_key_configured ? "••••••••••••••••" : "Enter Azure Key"}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-sm text-zinc-300">Azure Speech Region</label>
                <input 
                  type="text" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.azure_speech_region} 
                  onChange={e => setConfigSettings({...configSettings, azure_speech_region: e.target.value})}
                  placeholder="E.g. eastus, southeastasia"
                />
              </div>

              <div className="form-group flex flex-col gap-2 sm:col-span-2">
                <label className="form-label text-sm text-zinc-300">Sarvam AI API Key</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.sarvam_api_key} 
                  onChange={e => setConfigSettings({...configSettings, sarvam_api_key: e.target.value})}
                  placeholder={activeConfigStatus.sarvam_api_key_configured ? "••••••••••••••••" : "Enter Sarvam AI API Key"}
                />
              </div>

              <div className="form-group flex flex-col gap-2 sm:col-span-2">
                <label className="form-label text-sm text-zinc-300">Cloudinary Upload URL (CLOUDINARY_URL)</label>
                <input 
                  type="password" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  value={configSettings.cloudinary_url} 
                  onChange={e => setConfigSettings({...configSettings, cloudinary_url: e.target.value})}
                  placeholder={activeConfigStatus.cloudinary_url_configured ? "••••••••••••••••" : "cloudinary://api_key:api_secret@cloud_name"}
                />
                <small className="text-zinc-500 text-xs mt-1">
                  API connection string format: <code>cloudinary://api_key:api_secret@cloud_name</code>
                </small>
              </div>
            </div>

            {/* Queue & Concurrency Limits */}
            <div className="border-t border-white/5 pt-6 mt-6">
              <h3 className="text-base md:text-lg font-bold text-zinc-100 flex items-center gap-2 mb-4">
                <Cpu size={20} className="text-yellow-400" />
                Queue & Concurrency Configuration
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div className="form-group flex flex-col gap-2">
                  <label className="form-label text-sm text-zinc-300">Max Concurrent Tasks</label>
                  <input 
                    type="number" 
                    className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                    value={configSettings.max_concurrent_tasks} 
                    onChange={e => setConfigSettings({...configSettings, max_concurrent_tasks: parseInt(e.target.value) || 0})}
                    min="1"
                    placeholder="e.g. 5"
                  />
                  <small className="text-zinc-500 text-xs">
                    Maximum number of videos to compile in parallel.
                  </small>
                </div>

                <div className="form-group flex flex-col gap-2">
                  <label className="form-label text-sm text-zinc-300">Max Queued Tasks</label>
                  <input 
                    type="number" 
                    className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                    value={configSettings.max_queued_tasks} 
                    onChange={e => setConfigSettings({...configSettings, max_queued_tasks: parseInt(e.target.value) || 0})}
                    min="1"
                    placeholder="e.g. 100"
                  />
                  <small className="text-zinc-500 text-xs">
                    Maximum size of backlog queue for waiting videos.
                  </small>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-6 mt-6 border-t border-white/5">
            <button 
              type="submit" 
              className="btn btn-primary px-6 py-3 rounded-xl font-bold text-sm shadow-lg shadow-yellow-500/10 active:scale-95 transition-all" 
              disabled={isSavingSettings}
            >
              {isSavingSettings ? 'Applying Settings...' : 'Save Configuration'}
            </button>
          </div>
        </form>

        {/* Integration Health Panel (Right) */}
        <div className="flex flex-col gap-6">
          <div className="glass-panel p-6 flex flex-col">
            <h3 className="text-base md:text-lg font-bold text-zinc-100 mb-5">Integration Health Panel</h3>
            
            <div className="space-y-4">
              {[
                { name: 'Gemini LLM Engine', status: activeConfigStatus.gemini_api_key_configured, optional: false },
                { name: 'Gemini Fallback 2', status: activeConfigStatus.gemini_api_key_2_configured, optional: true },
                { name: 'Gemini Fallback 3', status: activeConfigStatus.gemini_api_key_3_configured, optional: true },
                { name: 'Gemini Fallback 4', status: activeConfigStatus.gemini_api_key_4_configured, optional: true },
                { name: 'Gemini Fallback 5', status: activeConfigStatus.gemini_api_key_5_configured, optional: true },
                { name: 'Pexels Visuals Stock', status: activeConfigStatus.pexels_api_key_configured, optional: false },
                { name: 'Azure Premium Speech', status: activeConfigStatus.azure_speech_key_configured, optional: false },
                { name: 'Sarvam Premium Speech', status: activeConfigStatus.sarvam_api_key_configured, optional: false },
                { name: 'Cloudinary CDN Storage', status: activeConfigStatus.cloudinary_url_configured, optional: false },
              ].map((item, idx) => (
                <div key={idx} className="flex justify-between items-center pb-3 border-b border-white/5 last:border-0 last:pb-0">
                  <span className="text-xs md:text-sm text-zinc-400">{item.name}</span>
                  <span className={`
                    px-2.5 py-0.5 rounded-full text-[10px] font-bold border
                    ${item.status 
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                      : item.optional 
                        ? 'bg-white/5 text-zinc-500 border-white/5' 
                        : 'bg-red-500/10 text-red-400 border-red-500/20'}
                  `}>
                    {item.status ? 'Configured' : item.optional ? 'Unset' : 'Offline'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel p-5 bg-blue-500/[0.02] border-blue-500/10 flex items-start gap-3">
            <Info size={16} className="text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs md:text-sm text-zinc-400 leading-relaxed">
              <h4 className="font-bold text-blue-400 mb-1">NeonDB Relational Persistence</h4>
              Unlike config files, this dashboard loads and overrides Pexels, Gemini, and Azure API configurations on-the-fly directly inside NeonDB, supporting headless production scaling.
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
