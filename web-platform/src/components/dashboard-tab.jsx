import React, { useRef, useEffect } from 'react';
import { 
  Tv, 
  RefreshCw, 
  Cloud,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react';

export default function DashboardTab({ 
  tasks, 
  youtubeStatus, 
  logs, 
  fetchTasksList, 
  selectedTask, 
  setSelectedTask 
}) {
  const consoleEndRef = useRef(null);

  // Auto-scroll console terminal to bottom on log updates
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  return (
    <div className="space-y-8 animate-fade-in">
      <header className="page-header">
        <h2 className="page-title text-2xl md:text-3xl font-extrabold">Operational SaaS Dashboard</h2>
        <p className="page-subtitle text-zinc-400 text-sm md:text-base">Track video transformations, cloud CDN uploads, and publish events in real-time.</p>
      </header>

      {/* Responsive Stats summary list */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="glass-panel p-6 flex flex-col gap-2">
          <span className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">Platform Task Ledger</span>
          <span className="text-3xl md:text-4xl font-extrabold text-zinc-100">{tasks.length}</span>
        </div>
        <div className="glass-panel p-6 flex flex-col gap-2">
          <span className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">Cloud CDN Assets</span>
          <span className="text-3xl md:text-4xl font-extrabold text-emerald-400">
            {tasks.filter(t => t.cloudinary_url).length} Uploads
          </span>
        </div>
        <div className="glass-panel p-6 flex flex-col gap-2 sm:col-span-2 lg:col-span-1">
          <span className="text-zinc-400 text-xs font-semibold uppercase tracking-wider">YouTube Connected</span>
          <span className={`text-2xl md:text-3xl font-extrabold truncate ${youtubeStatus.channel_connected ? 'text-emerald-400' : 'text-red-400'}`}>
            {youtubeStatus.channel_connected ? youtubeStatus.channel_name || 'Channel Linked' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Live active queue details & Console logs */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-8">
        
        {/* Relational Task Ledger list (Left) */}
        <div className="glass-panel p-6 xl:col-span-3 flex flex-col">
          <div className="flex items-center justify-between gap-4 mb-6">
            <h3 className="text-base md:text-lg font-bold text-zinc-200">Relational Task Ledger</h3>
            <button 
              className="btn btn-secondary px-3 py-1.5 text-xs flex items-center gap-1.5 text-zinc-300 hover:text-white"
              onClick={fetchTasksList}
            >
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
          
          <div className="space-y-4 max-h-[420px] overflow-y-auto pr-1">
            {tasks.length === 0 ? (
              <div className="py-10 text-center text-zinc-500 text-sm">
                No tasks found in NeonDB database.
              </div>
            ) : (
              tasks.map((task) => {
                const isActive = selectedTask && selectedTask.task_id === task.task_id;
                return (
                  <div 
                    key={task.task_id} 
                    onClick={() => setSelectedTask(task)}
                    className={`
                      flex flex-col gap-3 p-4.5 rounded-xl cursor-pointer transition-all border
                      ${isActive 
                        ? 'bg-yellow-500/3 border-yellow-500/30' 
                        : 'bg-white/[0.01] border-white/5 hover:border-white/10'}
                    `}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="font-bold text-sm md:text-base text-zinc-100 truncate flex items-center gap-2">
                          {task.params?.video_subject || 'Video Script Task'}
                          {task.cloudinary_url && <Cloud size={14} className="text-emerald-400 flex-shrink-0" title="Cloud CDN Host Available" />}
                        </div>
                        <div className="text-[10px] md:text-xs text-zinc-500 truncate">ID: {task.task_id}</div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 sm:self-center">
                        <span className="text-xs text-zinc-300 font-medium whitespace-nowrap">Progress: {task.progress || 0}%</span>
                        
                        {task.state === 1 && (
                          task.youtube_uploaded === 1 ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">YouTube Live</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/5 text-zinc-400 border border-white/10">Draft</span>
                          )
                        )}
                        {task.state === 1 && <span className="badge badge-success px-2 py-0.5 text-[10px]">Success</span>}
                        {task.state === 0 && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">Queued</span>}
                        {task.state === 4 && <span className="badge badge-warning px-2 py-0.5 text-[10px]">Stitching...</span>}
                        {(task.state === -1 || task.state === 2) && <span className="badge badge-danger px-2 py-0.5 text-[10px]">Failed</span>}
                        {task.state === 3 && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-yellow-400/10 text-yellow-400 border border-yellow-400/20">Stopped</span>}
                      </div>
                    </div>

                    {/* Detailed Error Stack trace wrapper */}
                    {(task.state === -1 || task.state === 2) && task.error_message && (
                      <div className="bg-red-500/5 border border-red-500/15 rounded-lg p-3 text-xs text-red-300 flex items-start gap-2">
                        <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-red-400" />
                        <div className="overflow-x-auto min-w-0 flex-1">
                          <strong className="block mb-1">Error Stack Trace:</strong>
                          <pre className="text-[10px] leading-relaxed font-mono whitespace-pre-wrap word-break-all">{task.error_message}</pre>
                          <span className="block text-[9px] opacity-60 mt-1.5">
                            Tip: Verify your API keys in the Settings tab are correct and not rate-limited.
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Cloud CDN play reminder */}
                    {task.cloudinary_url && (
                      <div className="text-xs text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle size={12} className="flex-shrink-0" />
                        <span className="truncate">CDN URL: <a href={task.cloudinary_url} target="_blank" rel="noreferrer" className="underline hover:text-emerald-300">{task.cloudinary_url}</a></span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Real-time Action Log console list (Right) */}
        <div className="glass-panel p-6 xl:col-span-2 flex flex-col">
          <h3 className="text-base md:text-lg font-bold text-zinc-200 mb-6">Real-time Action Log</h3>
          <div className="console-box flex-1 min-h-[250px] max-h-[420px] overflow-y-auto">
            {logs.map((log, index) => (
              <div key={index} className="mb-2.5 break-words text-xs md:text-[13px]">{log}</div>
            ))}
            <div ref={consoleEndRef} />
          </div>
        </div>

      </div>
    </div>
  );
}
