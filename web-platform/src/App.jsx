import React, { useState, useEffect } from 'react';
import { 
  Tv, 
  Video, 
  Database, 
  Clock, 
  Activity, 
  Cpu, 
  Loader2, 
  Music, 
  Compass, 
  Play, 
  Download, 
  RefreshCw, 
  Sparkles,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Info,
  Terminal,
  FileText,
  Volume2,
  Type,
  Film,
  Pause,
  Trash2,
  Mail,
  X,
  Cloud
} from 'lucide-react';
import { SignedIn, SignedOut, SignIn, UserButton, useUser, useAuth } from '@clerk/clerk-react';

import Sidebar from './components/sidebar';
import DashboardTab from './components/dashboard-tab';
import StudioTab from './components/studio-tab';
import SettingsTab from './components/settings-tab';
import PublishTab from './components/publish-tab';
import LibraryTab from './components/library-tab';
import Visualizer from './components/visualizer';
import AdminTab from './components/admin-tab';

// Use relative URLs so all requests go through the Vite dev proxy (vite.config.js).
// This avoids CORS entirely during local development.
// In production, these paths resolve against the same origin that serves the app.
const BACKEND_URL = '/api/v1';
const STREAM_URL = '';


const getTaskTitle = (task) => {
  if (task.params?.video_subject) {
    return task.params.video_subject;
  }
  if (task.terms) {
    try {
      let termsVal = task.terms;
      if (typeof termsVal === 'string') {
        if (termsVal.startsWith('[') || termsVal.startsWith('{')) {
          try {
            const parsed = JSON.parse(termsVal);
            if (Array.isArray(parsed) && parsed.length > 0) {
              return parsed[0];
            }
          } catch (e) {}
        }
        const cleanTerms = termsVal.replace(/[{}"']/g, '');
        const termsList = cleanTerms.split(',').map(t => t.trim()).filter(Boolean);
        if (termsList.length > 0) {
          return termsList[0];
        }
      } else if (Array.isArray(termsVal) && termsVal.length > 0) {
        return termsVal[0];
      }
    } catch (e) {}
  }
  if (task.script) {
    const firstSentence = task.script.split(/[.!?]/)[0].trim();
    const words = firstSentence.split(/\s+/);
    if (words.length > 6) {
      return words.slice(0, 6).join(' ') + '...';
    }
    return firstSentence;
  }
  return 'Compiled Short Video';
};

export default function App() {
  const { user, isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [quotaInfo, setQuotaInfo] = useState({
    quota_videos_per_day: 5,
    usage_today: 0
  });

  const getHeaders = async (extraHeaders = {}) => {
    const headers = { ...extraHeaders };
    if (isSignedIn) {
      try {
        const token = await getToken();
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      } catch (err) {
        console.error("Failed to get Clerk token:", err);
      }
    }
    if (user) {
      headers['X-User-Id'] = user.id;
    }
    
    // Add YouTube tokens from localStorage if they exist
    const ytAccessToken = localStorage.getItem('youtube_access_token');
    const ytRefreshToken = localStorage.getItem('youtube_refresh_token');
    const ytChannelName = localStorage.getItem('youtube_channel_name');
    const ytChannelId = localStorage.getItem('youtube_channel_id');
    if (ytAccessToken && ytRefreshToken && ytChannelName && ytChannelId) {
      headers['X-YouTube-Access-Token'] = ytAccessToken;
      headers['X-YouTube-Refresh-Token'] = ytRefreshToken;
      headers['X-YouTube-Channel-Name'] = ytChannelName;
      headers['X-YouTube-Channel-Id'] = ytChannelId;
    }
    
    return headers;
  };

  const [tasks, setTasks] = useState([]);
  const [bgmFiles, setBgmFiles] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [youtubeStatus, setYoutubeStatus] = useState({
    client_secret_exists: false,
    token_exists: false,
    channel_connected: false,
    channel_name: ''
  });
  const [tiktokStatus, setTiktokStatus] = useState({
    channel_connected: false,
    channel_name: ''
  });
  const [instagramStatus, setInstagramStatus] = useState({
    channel_connected: false,
    channel_name: ''
  });
  const [scheduledPosts, setScheduledPosts] = useState([]);
  const [isLoadingSchedule, setIsLoadingSchedule] = useState(false);
  
  // App settings state
  const [configSettings, setConfigSettings] = useState({
    gemini_api_key: '',
    gemini_api_key_2: '',
    gemini_api_key_3: '',
    gemini_api_key_4: '',
    gemini_api_key_5: '',
    pexels_api_key: '',
    azure_speech_key: '',
    azure_speech_region: 'eastus',
    sarvam_api_key: '',
    cloudinary_url: '',
    max_concurrent_tasks: 5,
    max_queued_tasks: 100,
  });

  const [activeConfigStatus, setActiveConfigStatus] = useState({
    gemini_api_key_configured: false,
    gemini_api_key_2_configured: false,
    gemini_api_key_3_configured: false,
    gemini_api_key_4_configured: false,
    gemini_api_key_5_configured: false,
    pexels_api_key_configured: false,
    azure_speech_key_configured: false,
    azure_speech_region: '',
    sarvam_api_key_configured: false,
    cloudinary_url_configured: false,
  });

  const [logs, setLogs] = useState([
    'System Initialized',
    'Connected to relational NeonDB metadata cluster',
    'Ready for cloud uploading & video pipeline generation'
  ]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [activeVideo, setActiveVideo] = useState(null);
  const [clientSecretFile, setClientSecretFile] = useState(null);
  const [isUploadingSecret, setIsUploadingSecret] = useState(false);
  const [uploadingTasks, setUploadingTasks] = useState({});
  const [isPreviewingVoice, setIsPreviewingVoice] = useState(false);

  // Studio form states
  const [studioParams, setStudioParams] = useState({
    video_subject: 'The Power of Consistency',
    video_aspect: '9:16',
    video_clip_duration: 3,
    video_source: 'pexels',
    video_language: '',
    voice_name: 'en-US-AndrewNeural',
    font_name: 'Poppins-Bold.ttf',
    text_fore_color: '#FFD700',
    stroke_color: '#000000',
    bgm_type: 'random',
    bgm_file: '',
    bgm_volume: 0.15,
    subtitle_enabled: true,
    text_background_color: false,
    video_duration: 30,
    prompt_mode: 'viral_shorts',
    target_platform: 'youtube_shorts',
    emotional_tone: 'inspiring',
    trend_context: '',
    video_script: '',
    color_grade_preset: 'none',
    beat_sync: false,
    subtitle_animation: 'static',
    emoji_subtitles: false,
    ken_burns: true
  });

  // Query tab param on startup (for youtube oauth callbacks redirect)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tabParam = params.get('tab');
    
    // Check for YouTube callback parameters to sync in localStorage
    const ytAccessToken = params.get('youtube_access_token');
    const ytRefreshToken = params.get('youtube_refresh_token');
    const ytChannelName = params.get('youtube_channel_name');
    const ytChannelId = params.get('youtube_channel_id');
    
    if (ytAccessToken && ytRefreshToken && ytChannelName && ytChannelId) {
      localStorage.setItem('youtube_access_token', ytAccessToken);
      localStorage.setItem('youtube_refresh_token', ytRefreshToken);
      localStorage.setItem('youtube_channel_name', ytChannelName);
      localStorage.setItem('youtube_channel_id', ytChannelId);
      addLog(`YouTube channel linked via local storage: ${decodeURIComponent(ytChannelName)}`);
    }

    if (tabParam) {
      setActiveTab(tabParam);
      // Clean query strings without page refresh
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const addLog = (msg) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [`[${timestamp}] ${msg}`, ...prev]);
  };

  // Fetch API Settings configuration from NeonDB
  const fetchSettings = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/settings`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setActiveConfigStatus(data.data);
        setConfigSettings(prev => ({
          ...prev,
          azure_speech_region: data.data.azure_speech_region || prev.azure_speech_region,
          max_concurrent_tasks: data.data.max_concurrent_tasks || prev.max_concurrent_tasks,
          max_queued_tasks: data.data.max_queued_tasks || prev.max_queued_tasks
        }));
        setQuotaInfo({
          quota_videos_per_day: data.data.quota_videos_per_day || 5,
          usage_today: data.data.usage_today || 0
        });
      }
    } catch (e) {
      addLog(`Failed to query platform settings: ${e.message}`);
    }
  };

  const checkAdminRole = async () => {
    if (!isSignedIn) {
      setIsAdmin(false);
      return;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/admin/stats`, {
        headers: await getHeaders()
      });
      if (res.status === 200) {
        setIsAdmin(true);
      } else {
        setIsAdmin(false);
      }
    } catch (e) {
      setIsAdmin(false);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setIsSavingSettings(true);
    addLog("Updating NeonDB platform settings configuration dynamically...");
    try {
      const res = await fetch(`${BACKEND_URL}/settings`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(configSettings)
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog("NeonDB API and integration configurations updated successfully.");
        alert("Platform settings saved and applied successfully!");
        fetchSettings();
        fetchYoutubeStatus();
      } else {
        addLog(`Error saving settings: ${data.message}`);
      }
    } catch (err) {
      addLog(`Failed to connect to backend: ${err.message}`);
    } finally {
      setIsSavingSettings(false);
    }
  };

  const fetchBgmList = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/musics`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setBgmFiles(data.data.files || []);
      }
    } catch (e) {
      addLog(`Failed to fetch BGM list: ${e.message}`);
    }
  };

  const fetchYoutubeStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/youtube/status`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        if (data.data.channel_connected) {
          setYoutubeStatus(data.data);
        } else {
          const localChannelName = localStorage.getItem('youtube_channel_name');
          const localChannelId = localStorage.getItem('youtube_channel_id');
          if (localChannelName && localChannelId) {
            setYoutubeStatus({
              client_secret_exists: true,
              token_exists: true,
              channel_connected: true,
              channel_name: decodeURIComponent(localChannelName),
              channel_id: localChannelId
            });
          } else {
            setYoutubeStatus(data.data);
          }
        }
      }
    } catch (e) {
      addLog(`Failed to query YouTube status: ${e.message}`);
    }
  };

  const fetchTiktokStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/tiktok/status`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setTiktokStatus(data.data);
      }
    } catch (e) {
      addLog(`Failed to query TikTok status: ${e.message}`);
    }
  };

  const handleConnectTiktok = async () => {
    addLog("Requesting TikTok OAuth authentication URL...");
    try {
      const res = await fetch(`${BACKEND_URL}/tiktok/connect`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200 && data.data.auth_url) {
        addLog("Redirecting browser to secure TikTok authentication page...");
        window.location.href = data.data.auth_url;
      } else {
        alert("Failed to start TikTok OAuth flow.");
      }
    } catch (err) {
      addLog(`TikTok OAuth connection error: ${err.message}`);
      alert("Error starting TikTok OAuth flow: " + err.message);
    }
  };

  const handleDisconnectTiktok = async () => {
    if (!window.confirm("Are you sure you want to disconnect your TikTok account?")) return;
    addLog("Disconnecting TikTok channel...");
    try {
      const res = await fetch(`${BACKEND_URL}/tiktok/disconnect`, {
        method: 'POST',
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setTiktokStatus({ channel_connected: false, channel_name: '' });
        addLog("TikTok channel disconnected successfully.");
      }
    } catch (err) {
      addLog(`TikTok disconnect error: ${err.message}`);
    }
  };

  const fetchInstagramStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/instagram/status`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setInstagramStatus(data.data);
      }
    } catch (e) {
      addLog(`Failed to query Instagram status: ${e.message}`);
    }
  };

  const handleConnectInstagram = async () => {
    addLog("Requesting Instagram OAuth authentication URL...");
    try {
      const res = await fetch(`${BACKEND_URL}/instagram/connect`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200 && data.data.auth_url) {
        addLog("Redirecting browser to Facebook/Instagram authentication page...");
        window.location.href = data.data.auth_url;
      } else {
        alert("Failed to start Instagram OAuth flow.");
      }
    } catch (err) {
      addLog(`Instagram OAuth connection error: ${err.message}`);
      alert("Error starting Instagram OAuth flow: " + err.message);
    }
  };

  const handleDisconnectInstagram = async () => {
    if (!window.confirm("Are you sure you want to disconnect your Instagram account?")) return;
    addLog("Disconnecting Instagram account...");
    try {
      const res = await fetch(`${BACKEND_URL}/instagram/disconnect`, {
        method: 'POST',
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setInstagramStatus({ channel_connected: false, channel_name: '' });
        addLog("Instagram account disconnected successfully.");
      }
    } catch (err) {
      addLog(`Instagram disconnect error: ${err.message}`);
    }
  };

  const fetchScheduledPosts = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/schedule`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setScheduledPosts(data.data.posts || []);
      }
    } catch (e) {
      console.error("Failed to query scheduled posts:", e);
    }
  };

  const handleCancelSchedule = async (postId) => {
    if (!window.confirm("Are you sure you want to cancel this scheduled post?")) return;
    addLog(`Canceling scheduled post ID ${postId}...`);
    try {
      const res = await fetch(`${BACKEND_URL}/schedule/cancel/${postId}`, {
        method: 'POST',
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`Scheduled post ID ${postId} cancelled successfully.`);
        fetchScheduledPosts();
      } else {
        alert(`Failed to cancel scheduled post: ${data.message}`);
      }
    } catch (err) {
      addLog(`Cancel schedule connection error: ${err.message}`);
    }
  };

  const fetchTasksList = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/tasks?page=1&page_size=50`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        const list = data.data.tasks || [];
        setTasks(list);
        
        if (list.length > 0 && !selectedTask) {
          setSelectedTask(list[0]);
        } else if (list.length > 0 && selectedTask) {
          const updated = list.find(t => t.task_id === selectedTask.task_id);
          if (updated) {
            if (updated.status_message && updated.status_message !== selectedTask.status_message) {
              addLog(`[Backend Status] ${updated.status_message}`);
            }
            setSelectedTask(updated);
          }
        }
      }
    } catch (e) {
      addLog(`Failed to fetch tasks: ${e.message}`);
    }
  };

  useEffect(() => {
    fetchBgmList();
    fetchYoutubeStatus();
    fetchTiktokStatus();
    fetchInstagramStatus();
    fetchTasksList();
    fetchSettings();
    checkAdminRole();
    fetchScheduledPosts();
    
    const interval = setInterval(() => {
      fetchTasksList();
      fetchScheduledPosts();
    }, 5000);
    return () => clearInterval(interval);
  }, [user]);

  const handleGenerateVideo = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setIsLoading(true);
    addLog(`Creating dynamic SaaS video task: "${studioParams.video_subject}"`);
    try {
      const res = await fetch(`${BACKEND_URL}/videos`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          ...studioParams,
          video_script_prompt: "Create a highly engaging, emotional and punchy motivational transcript. Emphasize keywords. Keep sentences very short."
        })
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`Task pipeline initialized in NeonDB. ID: ${data.data.task_id}`);
        fetchTasksList();
        fetchSettings();
        
        const newTask = {
          task_id: data.data.task_id,
          progress: 5,
          state: 0,
          params: studioParams
        };
        setSelectedTask(newTask);
        setActiveTab('dashboard');
      } else {
        addLog(`Error creating task: ${data.message}`);
      }
    } catch (err) {
      addLog(`Network error creating task: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopTask = async (taskId) => {
    addLog(`Requesting to stop/pause task ${taskId}...`);
    try {
      const res = await fetch(`${BACKEND_URL}/tasks/${taskId}/stop`, {
        method: 'POST',
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`Task ${taskId} stopped successfully.`);
        fetchTasksList();
      } else {
        addLog(`Failed to stop task: ${data.message}`);
        alert(`Failed to stop task: ${data.message}`);
      }
    } catch (err) {
      addLog(`Failed to connect to backend: ${err.message}`);
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm("Are you sure you want to delete this task? This will permanently erase the database record and clean up files from disk.")) {
      return;
    }
    addLog(`Deleting task ${taskId}...`);
    try {
      const res = await fetch(`${BACKEND_URL}/tasks/${taskId}`, {
        method: 'DELETE',
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`Task ${taskId} deleted successfully.`);
        setSelectedTask(null);
        fetchTasksList();
      } else {
        addLog(`Failed to delete task: ${data.message}`);
        alert(`Failed to delete task: ${data.message}`);
      }
    } catch (err) {
      addLog(`Failed to connect to backend: ${err.message}`);
    }
  };

  const handleReinitTask = async (task) => {
    if (!task || !task.params) {
      alert("No parameters found to re-initialize task.");
      return;
    }
    addLog(`Re-initializing task pipeline for subject: "${task.params.video_subject}"`);
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/videos`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          ...task.params,
          video_script_prompt: "Create a highly engaging, emotional and punchy motivational transcript. Emphasize keywords. Keep sentences very short."
        })
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`New task pipeline initialized. ID: ${data.data.task_id}`);
        fetchTasksList();
        fetchSettings();
        
        const newTask = {
          task_id: data.data.task_id,
          progress: 5,
          state: 0,
          params: task.params
        };
        setSelectedTask(newTask);
      } else {
        addLog(`Failed to re-initialize task: ${data.message}`);
        alert(`Failed to re-initialize task: ${data.message}`);
      }
    } catch (err) {
      addLog(`Network error re-initializing task: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnectYoutube = async () => {
    addLog("Requesting Google YouTube Web OAuth authentication URL...");
    try {
      const res = await fetch(`${BACKEND_URL}/youtube/connect?user_id=${user ? user.id : 'global'}`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200 && data.data.auth_url) {
        addLog("Redirecting browser to secure Google Consent verification screen...");
        window.location.href = data.data.auth_url;
      } else {
        addLog(`OAuth URL retrieval failed: ${data.message || 'Config keys missing.'}`);
        alert(`Failed to start OAuth flow. Please ensure your global YouTube developer configurations are set up correctly!`);
      }
    } catch (err) {
      addLog(`OAuth connection error: ${err.message}`);
      alert("Error starting OAuth flow: " + err.message);
    }
  };

  const handleDisconnectYoutube = () => {
    localStorage.removeItem('youtube_access_token');
    localStorage.removeItem('youtube_refresh_token');
    localStorage.removeItem('youtube_channel_name');
    localStorage.removeItem('youtube_channel_id');
    setYoutubeStatus({
      client_secret_exists: true,
      token_exists: false,
      channel_connected: false,
      channel_name: ''
    });
    addLog("YouTube channel disconnected locally. Clear browser memory and server-side cash completed.");
  };

  const handleUploadClientSecret = async (e) => {
    e.preventDefault();
    if (!clientSecretFile) {
      alert("Please select a JSON file first.");
      return;
    }
    
    setIsUploadingSecret(true);
    addLog("Uploading new client_secret.json...");
    
    const formData = new FormData();
    formData.append("file", clientSecretFile);
    
    try {
      const res = await fetch(`${BACKEND_URL}/youtube/upload-secret`, {
        method: "POST",
        headers: await getHeaders(),
        body: formData,
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog("client_secret.json uploaded and parsed into settings database.");
        alert("Client secret file uploaded successfully! Configurations populated.");
        setClientSecretFile(null);
        fetchYoutubeStatus();
        fetchSettings();
      } else {
        addLog(`Upload failed: ${data.message}`);
        alert(`Upload failed: ${data.message}`);
      }
    } catch (err) {
      addLog(`Upload connection error: ${err.message}`);
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsUploadingSecret(false);
    }
  };

  const handleUploadTaskToYoutube = async (taskId) => {
    setUploadingTasks(prev => ({ ...prev, [taskId]: true }));
    addLog(`Initiating manual YouTube upload for task ${taskId}...`);
    try {
      const res = await fetch(`${BACKEND_URL}/youtube/upload-task/${taskId}`, {
        method: 'POST',
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`YouTube publishing started in background for task ${taskId}.`);
        alert("YouTube upload started in the background!");
      } else {
        addLog(`YouTube upload failed: ${data.message}`);
        alert(`Publish failed: ${data.message}`);
      }
    } catch (err) {
      addLog(`YouTube upload connection error: ${err.message}`);
      alert(`Upload connection error: ${err.message}`);
    } finally {
      setUploadingTasks(prev => ({ ...prev, [taskId]: false }));
    }
  };

  const handlePreviewVoice = async () => {
    setIsPreviewingVoice(true);
    addLog(`Playing voice preview for ${studioParams.voice_name}...`);
    try {
      const token = isSignedIn ? await getToken() : '';
      const audioUrl = `${STREAM_URL}/api/v1/voice/preview?voice=${studioParams.voice_name}&user_id=${user ? user.id : 'global'}&token=${token}`;
      const audio = new Audio(audioUrl);
      audio.onplay = () => {
        setIsPreviewingVoice(false);
      };
      audio.onerror = (e) => {
        setIsPreviewingVoice(false);
        alert("Failed to play preview. Verify backend connection.");
      };
      await audio.play();
    } catch (e) {
      addLog(`Failed to preview voice: ${e.message}`);
      setIsPreviewingVoice(false);
    }
  };

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-screen w-screen bg-zinc-950 text-white font-sans">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-spin inline-block">🎬</div>
          <div className="text-sm font-medium text-zinc-400 tracking-wider">Loading Turbo Studio...</div>
        </div>
      </div>
    );
  }

  // Clerk Signed Out Screen
  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white font-sans relative overflow-x-hidden flex flex-col justify-between">
        
        {/* Decorative background glows */}
        <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] rounded-full bg-purple-500/[0.04] blur-[100px] pointer-events-none" />
        <div className="absolute bottom-[10%] right-[10%] w-[600px] h-[600px] rounded-full bg-pink-500/[0.03] blur-[120px] pointer-events-none" />
        
        {/* Navigation Header */}
        <header className="flex items-center justify-between px-6 py-5 md:px-12 border-b border-white/5 backdrop-blur-md bg-zinc-950/70 z-10">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎬</span>
            <span className="text-lg md:text-xl font-extrabold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">Turbo Studio</span>
            <span className="bg-purple-500/10 text-purple-300 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-purple-500/20">SaaS Platform</span>
          </div>
        </header>

        {/* Hero split layout grid */}
        <main className="flex-grow flex items-center justify-center px-6 py-12 md:px-12 z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 max-w-6xl w-full items-center">
            
            {/* Title introduction features */}
            <div className="space-y-8">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold leading-tight tracking-tight">
                Generate & Publish <br/>
                <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">Viral Shorts</span> in Seconds
              </h1>
              <p className="text-zinc-400 text-base md:text-lg leading-relaxed">
                Turbo Studio is a state-of-the-art multi-tenant automation platform. Connect your YouTube account, synthesize rich voices, stitch high-fidelity stock reels automatically, and publish directly from our glassmorphic real-time dashboard.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  { title: 'AI Scriptwriting', icon: '🤖', desc: 'Instant motivational paragraphs via Gemini model configurations.' },
                  { title: 'TTS Voice Engine', icon: '🎙️', desc: 'Premium edge-tts / Azure TTS v2 narration & timing code generation.' },
                  { title: 'Intelligent Stitching', icon: '🎥', desc: 'Pexels/Pixabay keywords visual material downloads and FFmpeg rendering.' },
                  { title: 'CDN & Auto-Upload', icon: '☁️', desc: 'Cloudinary direct video assets hosting and direct YouTube OAuth publishing.' },
                ].map((f, idx) => (
                  <div key={idx} className="bg-white/[0.02] border border-white/5 p-4 rounded-xl space-y-1">
                    <span className="text-lg block mb-1">{f.icon}</span>
                    <h3 className="font-bold text-sm text-zinc-200">{f.title}</h3>
                    <p className="text-xs text-zinc-500 leading-normal">{f.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Authentication dialog */}
            <div className="flex justify-center relative">
              <div className="absolute inset-0 bg-purple-500/10 blur-[50px] rounded-full z-[-1]" />
              <div className="border border-white/5 shadow-2xl rounded-3xl overflow-hidden bg-zinc-900/50 backdrop-blur-md p-2">
                <SignIn routing="hash" />
              </div>
            </div>

          </div>
        </main>

        {/* Footer info bar */}
        <footer className="py-6 border-t border-white/5 text-center text-xs text-zinc-600 bg-zinc-950/20 z-10 px-6">
          <span>© 2026 Turbo Studio Automation SaaS. Persisted safely inside NeonDB relational tables.</span>
        </footer>

      </div>
    );
  }

  // Clerk Signed In Content Dashboard layout
  return (
    <div className="min-h-screen bg-zinc-950 text-white font-sans flex flex-col md:flex-row relative">
      
      {/* Sidebar Navigation */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        user={user} 
        sidebarOpen={sidebarOpen} 
        setSidebarOpen={setSidebarOpen} 
        isAdmin={isAdmin}
      />

      {/* Main Content Area */}
      <div className="flex-1 md:pl-[280px] min-h-screen flex flex-col w-full overflow-x-hidden">
        <main className="flex-grow p-6 md:p-10 max-w-7xl w-full mx-auto space-y-8">
          
          {/* Active visualizer block (Only visible on dashboard tab) */}
          {activeTab === 'dashboard' && (
            <Visualizer 
              selectedTask={selectedTask} 
              handleStopTask={handleStopTask}
              handleReinitTask={handleReinitTask}
              handleDeleteTask={handleDeleteTask}
              STREAM_URL={STREAM_URL}
              getToken={getToken}
            />
          )}

          {/* Render Tab Contents */}
          {activeTab === 'dashboard' && (
            <DashboardTab 
              tasks={tasks}
              youtubeStatus={youtubeStatus}
              logs={logs}
              fetchTasksList={fetchTasksList}
              selectedTask={selectedTask}
              setSelectedTask={setSelectedTask}
            />
          )}

          {activeTab === 'studio' && (
            <StudioTab 
              studioParams={studioParams}
              setStudioParams={setStudioParams}
              bgmFiles={bgmFiles}
              isLoading={isLoading}
              handleGenerateVideo={handleGenerateVideo}
              handlePreviewVoice={handlePreviewVoice}
              isPreviewingVoice={isPreviewingVoice}
              quotaInfo={quotaInfo}
              BACKEND_URL={BACKEND_URL}
              getHeaders={getHeaders}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsTab 
              configSettings={configSettings}
              setConfigSettings={setConfigSettings}
              activeConfigStatus={activeConfigStatus}
              handleSaveSettings={handleSaveSettings}
              isSavingSettings={isSavingSettings}
            />
          )}

          {activeTab === 'publish' && (
            <PublishTab 
              youtubeStatus={youtubeStatus}
              tiktokStatus={tiktokStatus}
              instagramStatus={instagramStatus}
              handleConnectYoutube={handleConnectYoutube}
              handleDisconnectYoutube={handleDisconnectYoutube}
              handleConnectTiktok={handleConnectTiktok}
              handleDisconnectTiktok={handleDisconnectTiktok}
              handleConnectInstagram={handleConnectInstagram}
              handleDisconnectInstagram={handleDisconnectInstagram}
              clientSecretFile={clientSecretFile}
              setClientSecretFile={setClientSecretFile}
              isUploadingSecret={isUploadingSecret}
              handleUploadClientSecret={handleUploadClientSecret}
              scheduledPosts={scheduledPosts}
              handleCancelSchedule={handleCancelSchedule}
              isLoadingSchedule={isLoadingSchedule}
              fetchScheduledPosts={fetchScheduledPosts}
            />
          )}

          {activeTab === 'library' && (
            <LibraryTab 
              tasks={tasks}
              youtubeStatus={youtubeStatus}
              tiktokStatus={tiktokStatus}
              instagramStatus={instagramStatus}
              uploadingTasks={uploadingTasks}
              handleUploadTaskToYoutube={handleUploadTaskToYoutube}
              handleDeleteTask={handleDeleteTask}
              setActiveVideo={setActiveVideo}
              STREAM_URL={STREAM_URL}
              getTaskTitle={getTaskTitle}
              addLog={addLog}
              getHeaders={getHeaders}
            />
          )}

          {activeTab === 'admin' && (
            <AdminTab 
              BACKEND_URL={BACKEND_URL}
              getHeaders={getHeaders}
              addLog={addLog}
            />
          )}

        </main>

        {/* Global Video Preview Dialog Modal (Popup player overlay) */}
        {activeVideo && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-6 z-[200] animate-fade-in">
            <div className="glass-panel border border-white/10 rounded-2xl bg-zinc-950/90 w-full max-w-[400px] flex flex-col relative max-h-[85vh]">
              {/* Header with Title and Close Trigger */}
              <div className="flex items-center justify-between p-4.5 border-b border-white/5">
                <h3 className="text-sm font-bold text-zinc-100 truncate pr-4" title={activeVideo.title}>
                  Preview: {activeVideo.title}
                </h3>
                <button 
                  onClick={() => setActiveVideo(null)}
                  className="p-1.5 rounded-full text-zinc-400 hover:text-white hover:bg-white/5 transition-all flex-shrink-0"
                >
                  <X size={16} />
                </button>
              </div>
              
              {/* Responsive Player Slot */}
              <div className="flex-1 overflow-hidden p-2 flex items-center justify-center bg-black/60 aspect-[9/16] rounded-b-2xl">
                <video 
                  src={activeVideo.url} 
                  controls 
                  autoPlay
                  className="max-h-full max-w-full rounded-lg object-contain" 
                />
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
