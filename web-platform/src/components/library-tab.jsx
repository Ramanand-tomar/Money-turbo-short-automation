import React from 'react';
import { 
  Cloud, 
  Download, 
  Play, 
  Trash2, 
  Loader2, 
  Calendar, 
  X, 
  Clock 
} from 'lucide-react';

const Youtube = ({ size = 20, ...props }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    {...props}
  >
    <path d="M2.5 17a24.12 24.12 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.56 49.56 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.12 24.12 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.55 49.55 0 0 1-16.2 0A2 2 0 0 1 2.5 17" />
    <polygon points="10 15 15 12 10 9" fill="currentColor" />
  </svg>
);

const Tiktok = ({ size = 20, ...props }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    {...props}
  >
    <path d="M9 12a4 4 0 1 0 4 4V4a5 5 0 0 0 5 5" />
  </svg>
);

const Instagram = ({ size = 20, ...props }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    {...props}
  >
    <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
    <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
  </svg>
);

export default function LibraryTab({
  tasks,
  youtubeStatus,
  tiktokStatus,
  instagramStatus,
  uploadingTasks,
  handleUploadTaskToYoutube,
  handleDeleteTask,
  setActiveVideo,
  STREAM_URL,
  getTaskTitle,
  addLog,
  getHeaders
}) {
  // No cached token state needed — getHeaders() fetches a fresh Clerk JWT on every call.
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [activeTaskId, setActiveTaskId] = React.useState('');
  const [selectedPlatforms, setSelectedPlatforms] = React.useState({
    youtube: true,
    tiktok: false,
    instagram: false
  });
  const [scheduledTime, setScheduledTime] = React.useState('');

  React.useEffect(() => {
    const fetchToken = async () => {
      if (getToken) {
        try {
          const t = await getToken();
          setToken(t || '');
        } catch (e) {
          console.error("Error fetching token for library tab:", e);
        }
      }
    };
    fetchToken();
  }, [getToken]);

  const libraryTasks = tasks.filter(t => t.state === 1 && (t.cloudinary_url || (t.videos && t.videos.length > 0)));

  const handleOpenScheduleModal = (taskId) => {
    setActiveTaskId(taskId);
    const now = new Date();
    now.setHours(now.getHours() + 1);
    
    // Get local ISO string offset
    const tzoffset = now.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(now - tzoffset)).toISOString().slice(0, 16);
    setScheduledTime(localISOTime);
    setIsModalOpen(true);
  };

  const handleSetOptimalTime = (platform) => {
    const now = new Date();
    now.setMinutes(0);
    now.setSeconds(0);
    
    if (platform === 'youtube') {
      now.setHours(19); // 7:00 PM local
    } else if (platform === 'tiktok') {
      now.setHours(20); // 8:00 PM local
    } else if (platform === 'instagram') {
      now.setHours(12); // 12:00 PM local
    }
    
    if (now <= new Date()) {
      now.setDate(now.getDate() + 1);
    }
    
    const tzoffset = now.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(now - tzoffset)).toISOString().slice(0, 16);
    setScheduledTime(localISOTime);
  };

  const submitSchedule = async () => {
    const platformsToSchedule = Object.keys(selectedPlatforms).filter(p => selectedPlatforms[p]);
    if (platformsToSchedule.length === 0) {
      alert("Please select at least one publishing platform!");
      return;
    }
    if (!scheduledTime) {
      alert("Please select a date and time!");
      return;
    }

    const localDate = new Date(scheduledTime);
    const utcTimeStr = localDate.toISOString();

    try {
      let successCount = 0;
      for (const platform of platformsToSchedule) {
        if (platform === 'youtube' && !youtubeStatus.channel_connected) {
          alert("YouTube channel is not connected. Skipping YouTube scheduling.");
          continue;
        }
        if (platform === 'tiktok' && (!tiktokStatus || !tiktokStatus.channel_connected)) {
          alert("TikTok account is not connected. Skipping TikTok scheduling.");
          continue;
        }
        if (platform === 'instagram' && (!instagramStatus || !instagramStatus.channel_connected)) {
          alert("Instagram account is not connected. Skipping Instagram scheduling.");
          continue;
        }

        const res = await fetch(`${STREAM_URL}/api/v1/schedule`, {
          method: 'POST',
          headers: await getHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            task_id: activeTaskId,
            platform: platform,
            scheduled_at: utcTimeStr
          })
        });
        const data = await res.json();
        if (data.status === 200) {
          successCount++;
        } else {
          console.error(`Failed to schedule for ${platform}: ${data.message}`);
        }
      }
      
      if (successCount > 0) {
        if (addLog) addLog(`Successfully scheduled task ${activeTaskId} for ${successCount} platform(s).`);
        alert("Posting schedule created successfully!");
        setIsModalOpen(false);
      } else {
        alert("Failed to schedule posting. Please verify platform connections.");
      }
    } catch (err) {
      alert("Network error scheduling post: " + err.message);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <header className="page-header">
        <h2 className="page-title text-2xl md:text-3xl font-extrabold">Cloud Video Library</h2>
        <p className="page-subtitle text-zinc-400 text-sm md:text-base">Preview compiled shorts stored on Cloudinary CDN for fast streaming.</p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {libraryTasks.length === 0 ? (
          <div className="glass-panel col-span-full p-10 text-center text-zinc-500 text-sm md:text-base">
            No compiled videos found. Complete video generation in the Video Studio first!
          </div>
        ) : (
          libraryTasks.map((task) => {
            const tokenQuery = token ? `?token=${token}` : '';
            const finalVideoUrl = task.cloudinary_url || (task.videos[0].startsWith('http') ? task.videos[0] : `${STREAM_URL}${task.videos[0]}${tokenQuery}`);
            const taskTitle = getTaskTitle(task);
            
            return (
              <div key={task.task_id} className="video-card glass-panel p-0 flex flex-col justify-between overflow-hidden border border-white/5 bg-zinc-950/40 rounded-2xl hover:border-white/10 hover:translate-y-[-2px] transition-all duration-300">
                
                <div className="aspect-[9/16] w-full bg-zinc-950 relative overflow-hidden group">
                  <video className="w-full h-full object-cover pointer-events-none opacity-80" src={finalVideoUrl} preload="metadata" />
                  
                  <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <button 
                      className="p-4 bg-yellow-400 text-zinc-950 rounded-full hover:scale-105 active:scale-95 transition-all shadow-lg shadow-yellow-400/20" 
                      onClick={() => setActiveVideo({ url: finalVideoUrl, title: taskTitle })}
                    >
                      <Play size={20} fill="currentColor" className="ml-0.5" />
                    </button>
                  </div>
                  
                  {task.cloudinary_url && (
                    <div className="absolute top-3.5 left-3.5 bg-emerald-500/90 text-white text-[9px] font-bold px-2 py-0.5 rounded flex items-center gap-1 shadow-sm">
                      <Cloud size={10} /> CDN HOSTED
                    </div>
                  )}

                  {task.youtube_uploaded === 1 ? (
                    <div className="absolute top-3.5 right-3.5 bg-emerald-500/90 text-white text-[9px] font-bold px-2 py-0.5 rounded flex items-center gap-1 shadow-sm">
                      <Youtube size={10} /> YOUTUBE LIVE
                    </div>
                  ) : (
                    <div className="absolute top-3.5 right-3.5 bg-white/10 backdrop-blur-md text-white text-[9px] font-bold px-2 py-0.5 rounded flex items-center gap-1 shadow-sm border border-white/10">
                      <Youtube size={10} /> DRAFT
                    </div>
                  )}
                </div>

                <div className="p-4.5 flex flex-col gap-3.5 bg-zinc-950/20">
                  <div className="flex items-start justify-between gap-3 min-w-0">
                    <h4 className="font-bold text-sm text-zinc-100 truncate flex-1" title={taskTitle}>
                      {taskTitle}
                    </h4>
                    <span className={`
                      text-[9px] font-bold px-2 py-0.5 rounded border-0 whitespace-nowrap self-start
                      ${task.youtube_uploaded === 1 
                        ? 'bg-emerald-500/10 text-emerald-400' 
                        : 'bg-white/5 text-zinc-400'}
                    `}>
                      {task.youtube_uploaded === 1 ? 'YouTube Live' : 'Draft'}
                    </span>
                  </div>

                  <div className="text-[10px] text-zinc-500 font-medium">ID: {task.task_id.substring(0, 8)}...</div>

                  <div className="grid grid-cols-3 gap-2 mt-1">
                    <a 
                      href={finalVideoUrl} 
                      target="_blank" 
                      rel="noreferrer" 
                      download 
                      className="col-span-1 flex"
                    >
                      <button className="btn btn-secondary w-full px-2 py-2 text-[11px] flex items-center justify-center gap-1 hover:text-white transition-all text-zinc-300">
                        <Download size={11} /> File
                      </button>
                    </a>
                    
                    <button 
                      disabled={uploadingTasks[task.task_id]}
                      onClick={() => {
                        if (!youtubeStatus.channel_connected) {
                          alert("Please link your YouTube channel in the 'Publishing Hub' tab first!");
                          if (addLog) addLog("YouTube upload blocked: No channel linked.");
                          return;
                        }
                        if (task.youtube_uploaded === 1) {
                          const confirmPublish = window.confirm("This video has already been published to YouTube. Do you want to publish it again?");
                          if (!confirmPublish) return;
                        }
                        handleUploadTaskToYoutube(task.task_id);
                      }}
                      className={`
                        col-span-1 btn text-[11px] font-bold flex items-center justify-center gap-1 active:scale-95 transition-all
                        ${task.youtube_uploaded === 1 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20' 
                          : 'bg-red-500 text-white hover:bg-red-600 shadow-md shadow-red-500/5'}
                      `}
                    >
                      <Youtube size={11} /> 
                      {uploadingTasks[task.task_id] ? 'Syncing' : (task.youtube_uploaded === 1 ? 'Live' : 'Publish')}
                    </button>
 
                    <button
                      onClick={() => handleDeleteTask(task.task_id)}
                      className="col-span-1 btn btn-danger px-2 py-2 text-[11px] flex items-center justify-center gap-1 border border-red-500/10 hover:border-red-500/20 bg-red-500/5 hover:bg-red-500/10 text-red-400"
                    >
                      <Trash2 size={11} /> Delete
                    </button>
                  </div>

                  <button 
                    onClick={() => handleOpenScheduleModal(task.task_id)}
                    className="btn btn-secondary w-full mt-2.5 px-3 py-2 text-[11px] font-semibold flex items-center justify-center gap-1.5 text-yellow-400 border-yellow-500/10 hover:bg-yellow-400/5 hover:border-yellow-400/20"
                  >
                    <Calendar size={12} /> Schedule Posting
                  </button>
                </div>

              </div>
            );
          })
        )}
      </div>

      {/* Schedule Post Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center z-[150] animate-fade-in p-4">
          <div className="glass-panel max-w-md w-full p-6 md:p-8 space-y-6 relative border border-white/10 bg-zinc-950/95 shadow-2xl rounded-2xl">
            <button 
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-white p-1 hover:bg-white/5 rounded-full transition-colors"
            >
              <X size={18} />
            </button>

            <div>
              <h3 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
                <Calendar size={20} className="text-yellow-400" />
                Schedule Viral Posting
              </h3>
              <p className="text-xs text-zinc-400 mt-1">Select platforms and optimal hours to schedule your video publish event.</p>
            </div>

            <div className="space-y-4">
              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300 uppercase tracking-wider">Target Platforms</label>
                <div className="grid grid-cols-3 gap-2.5">
                  <button 
                    onClick={() => setSelectedPlatforms(prev => ({ ...prev, youtube: !prev.youtube }))}
                    className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all text-xs ${
                      selectedPlatforms.youtube 
                        ? 'bg-red-500/10 border-red-500/30 text-red-400 font-bold' 
                        : 'bg-zinc-900/50 border-white/5 text-zinc-500'
                    }`}
                  >
                    <Youtube size={16} /> Shorts
                  </button>
                  <button 
                    onClick={() => setSelectedPlatforms(prev => ({ ...prev, tiktok: !prev.tiktok }))}
                    className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all text-xs ${
                      selectedPlatforms.tiktok 
                        ? 'bg-teal-500/10 border-teal-500/30 text-teal-400 font-bold' 
                        : 'bg-zinc-900/50 border-white/5 text-zinc-500'
                    }`}
                  >
                    <Tiktok size={16} /> TikTok
                  </button>
                  <button 
                    onClick={() => setSelectedPlatforms(prev => ({ ...prev, instagram: !prev.instagram }))}
                    className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all text-xs ${
                      selectedPlatforms.instagram 
                        ? 'bg-pink-500/10 border-pink-500/30 text-pink-400 font-bold' 
                        : 'bg-zinc-900/50 border-white/5 text-zinc-500'
                    }`}
                  >
                    <Instagram size={16} /> Reels
                  </button>
                </div>
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300 uppercase tracking-wider">Scheduled Date & Time</label>
                <input 
                  type="datetime-local" 
                  value={scheduledTime}
                  onChange={e => setScheduledTime(e.target.value)}
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer text-xs md:text-sm"
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-500 uppercase tracking-wider">Post at Optimal Hours</label>
                <div className="flex flex-wrap gap-2">
                  <button 
                    onClick={() => handleSetOptimalTime('youtube')}
                    className="px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-white/5 text-[10px] text-zinc-300 hover:border-yellow-400/40 hover:bg-yellow-400/5 transition-all"
                  >
                    YouTube Shorts (7 PM)
                  </button>
                  <button 
                    onClick={() => handleSetOptimalTime('tiktok')}
                    className="px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-white/5 text-[10px] text-zinc-300 hover:border-yellow-400/40 hover:bg-yellow-400/5 transition-all"
                  >
                    TikTok (8 PM)
                  </button>
                  <button 
                    onClick={() => handleSetOptimalTime('instagram')}
                    className="px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-white/5 text-[10px] text-zinc-300 hover:border-yellow-400/40 hover:bg-yellow-400/5 transition-all"
                  >
                    IG Reels (12 PM)
                  </button>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-white/5 flex gap-4">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="btn btn-secondary flex-1 py-3 text-xs"
              >
                Cancel
              </button>
              <button 
                onClick={submitSchedule}
                className="btn btn-primary flex-1 py-3 text-xs text-black font-bold"
              >
                Schedule Post
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
