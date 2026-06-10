import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Loader2, 
  AlertTriangle, 
  Zap, 
  Star, 
  Brain, 
  BookOpen, 
  List, 
  TrendingUp,
  BarChart2,
  Lightbulb,
  ArrowRight,
  RefreshCw,
  Play,
  Film,
  Music,
  Type,
  Flame,
  Globe
} from 'lucide-react';

// Custom YouTube Icon
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

const PROMPT_MODES = [
  { id: 'viral_shorts', title: 'Viral Shorts', desc: 'Fast pacing & high-retention hooks', icon: Zap, color: 'from-amber-500 to-orange-600 border-orange-500/20 hover:border-orange-500/40 text-orange-400' },
  { id: 'motivational', title: 'Motivational', desc: 'Emotionally building & inspiring', icon: Star, color: 'from-rose-500 to-red-600 border-red-500/20 hover:border-red-500/40 text-red-400' },
  { id: 'educational', title: 'Educational', desc: 'Fascinating facts & simple analogies', icon: Brain, color: 'from-emerald-500 to-teal-600 border-emerald-500/20 hover:border-emerald-500/40 text-emerald-400' },
  { id: 'storytelling', title: 'Storytelling', desc: 'Narrative-driven drama & lessons', icon: BookOpen, color: 'from-blue-500 to-indigo-600 border-blue-500/20 hover:border-blue-500/40 text-blue-400' },
  { id: 'listicle', title: 'Listicle', desc: 'Fast, structured, rapid point lists', icon: List, color: 'from-violet-500 to-purple-600 border-purple-500/20 hover:border-purple-500/40 text-purple-400' },
  { id: 'trending_topic', title: 'Trending Topic', desc: 'Commentary on current viral news', icon: TrendingUp, color: 'from-fuchsia-500 to-pink-600 border-pink-500/20 hover:border-pink-500/40 text-pink-400' }
];

const CATEGORIES = [
  { id: 'all', name: 'All' },
  { id: 'motivation', name: 'Motivation' },
  { id: 'finance', name: 'Finance' },
  { id: 'health', name: 'Health' },
  { id: 'tech', name: 'Tech' },
  { id: 'entertainment', name: 'Entertainment' }
];

const MetricBar = ({ name, score, color }) => {
  const width = `${score * 10}%`;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-semibold text-zinc-300">
        <span>{name}</span>
        <span className="text-yellow-400 font-bold">{score}/10</span>
      </div>
      <div className="h-2 w-full bg-zinc-900/80 rounded-full overflow-hidden border border-white/5">
        <div 
          className={`h-full bg-gradient-to-r ${color} rounded-full transition-all duration-1000 ease-out shadow-md`}
          style={{ width }}
        />
      </div>
    </div>
  );
};

export default function StudioTab({ 
  studioParams, 
  setStudioParams, 
  bgmFiles, 
  isLoading, 
  handleGenerateVideo, 
  handlePreviewVoice, 
  isPreviewingVoice,
  quotaInfo,
  BACKEND_URL,
  getHeaders
}) {
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [isScoringScript, setIsScoringScript] = useState(false);
  const [score, setScore] = useState(null);
  const [scoreError, setScoreError] = useState(null);

  // Trending state variables
  const [trends, setTrends] = useState([]);
  const [activePlatform, setActivePlatform] = useState('google');
  const [activeCategory, setActiveCategory] = useState('all');
  const [isFetchingTrends, setIsFetchingTrends] = useState(false);

  const fetchTrends = async (platform, category) => {
    setIsFetchingTrends(true);
    try {
      const res = await fetch(`${BACKEND_URL}/trends?platform=${platform}&category=${category}`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setTrends(data.data.trends || []);
      }
    } catch (e) {
      console.error("Failed to fetch trending topics:", e);
    } finally {
      setIsFetchingTrends(false);
    }
  };

  useEffect(() => {
    fetchTrends(activePlatform, activeCategory);
  }, [activePlatform, activeCategory]);

  const handleSelectTrend = (topic) => {
    setStudioParams(prev => ({
      ...prev,
      video_subject: topic
    }));
  };

  const handleRefreshTrends = () => {
    fetchTrends(activePlatform, activeCategory);
  };

  const handleDraftScript = async () => {
    if (!studioParams.video_subject) {
      alert("Please enter a Video Subject/Theme first!");
      return;
    }
    setIsGeneratingScript(true);
    setScore(null);
    setScoreError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/scripts`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          video_subject: studioParams.video_subject,
          video_language: studioParams.video_language,
          paragraph_number: 1,
          video_script_prompt: '',
          custom_system_prompt: '',
          prompt_mode: studioParams.prompt_mode,
          target_platform: studioParams.target_platform,
          emotional_tone: studioParams.emotional_tone,
          trend_context: studioParams.trend_context
        })
      });
      const data = await res.json();
      if (data.status === 200 && data.data?.video_script) {
        setStudioParams(prev => ({
          ...prev,
          video_script: data.data.video_script
        }));
      } else {
        alert("Failed to draft script: " + (data.message || "Unknown error"));
      }
    } catch (err) {
      alert("Network error drafting script: " + err.message);
    } finally {
      setIsGeneratingScript(false);
    }
  };

  const handleScoreScript = async () => {
    if (!studioParams.video_script) {
      alert("Please generate or write a script first!");
      return;
    }
    setIsScoringScript(true);
    setScoreError(null);
    try {
      const res = await fetch(`${BACKEND_URL}/scripts/score`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          script: studioParams.video_script,
          platform: studioParams.target_platform
        })
      });
      const data = await res.json();
      if (data.status === 200) {
        setScore(data.data);
      } else {
        setScoreError(data.message || "Failed to score script");
      }
    } catch (err) {
      setScoreError(err.message);
    } finally {
      setIsScoringScript(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <header className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="page-title text-2xl md:text-3xl font-extrabold bg-gradient-to-r from-yellow-400 to-orange-500 bg-clip-text text-transparent">Dynamic Studio</h2>
          <p className="page-subtitle text-zinc-400 text-sm md:text-base">Configure video parameters dynamically. Compilation automatically hosts on Cloud CDN.</p>
        </div>
        {quotaInfo && (
          <div className="bg-zinc-900 border border-white/5 px-4 py-2.5 rounded-xl flex flex-col items-end justify-center self-start sm:self-auto flex-shrink-0">
            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Daily Quota</span>
            <span className="text-sm font-extrabold text-zinc-200">{quotaInfo.usage_today} / {quotaInfo.quota_videos_per_day} videos today</span>
          </div>
        )}
      </header>

      {quotaInfo && (quotaInfo.usage_today / quotaInfo.quota_videos_per_day) >= 0.8 && (
        <div className={`p-4 rounded-xl border flex items-center gap-3 ${
          quotaInfo.usage_today >= quotaInfo.quota_videos_per_day
            ? 'bg-red-500/10 border-red-500/20 text-red-200'
            : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-200'
        }`}>
          <AlertTriangle size={18} className="flex-shrink-0 animate-pulse" />
          <div className="text-xs md:text-sm font-medium">
            {quotaInfo.usage_today >= quotaInfo.quota_videos_per_day ? (
              <span><strong>Limit Reached:</strong> You have used all {quotaInfo.quota_videos_per_day} videos allowed for today. New requests will be blocked until UTC midnight.</span>
            ) : (
              <span><strong>Warning:</strong> You are reaching your daily generation limit. You have generated {quotaInfo.usage_today} out of {quotaInfo.quota_videos_per_day} allowed videos today.</span>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Side: Parameters Form */}
        <form onSubmit={handleGenerateVideo} className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-6 space-y-6">
            <h3 className="text-base font-bold border-b border-white/5 pb-3 flex items-center gap-2">
              <Film size={16} className="text-yellow-400" />
              Video Parameters
            </h3>

            {/* Video Prompt Theme */}
            <div className="form-group flex flex-col gap-2">
              <label className="form-label text-xs font-semibold text-zinc-300">Video Prompt / Motivational Theme</label>
              <input 
                type="text" 
                className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400/20 outline-none transition-all"
                value={studioParams.video_subject} 
                onChange={e => setStudioParams({...studioParams, video_subject: e.target.value})}
                placeholder="E.g. Why Consistent Habits Shape Your Mindset"
                required 
              />
            </div>

            {/* Prompt Mode Grid Selector */}
            <div className="form-group flex flex-col gap-2">
              <label className="form-label text-xs font-semibold text-zinc-300">Viral Script Writing Mode</label>
              <div className="grid grid-cols-1 gap-2">
                {PROMPT_MODES.map(mode => {
                  const Icon = mode.icon;
                  const isSelected = studioParams.prompt_mode === mode.id;
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => setStudioParams({ ...studioParams, prompt_mode: mode.id })}
                      className={`text-left p-3 rounded-xl border transition-all duration-300 flex items-start gap-2.5 relative ${
                        isSelected 
                          ? `bg-zinc-900 border-yellow-400/80 shadow-lg shadow-yellow-500/5 ring-1 ring-yellow-400/30` 
                          : 'bg-zinc-950/40 border-white/5 hover:bg-zinc-900/30'
                      }`}
                    >
                      <div className={`p-1.5 rounded-lg bg-zinc-900 border border-white/5 ${isSelected ? mode.color.split(' ')[4] : 'text-zinc-500'}`}>
                        <Icon size={14} />
                      </div>
                      <div className="space-y-0.5">
                        <span className="text-xs font-bold block text-zinc-200">{mode.title}</span>
                        <span className="text-[10px] text-zinc-500 block leading-normal">{mode.desc}</span>
                      </div>
                      {isSelected && (
                        <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Platform, Emotional Tone, Trend Context */}
            <div className="space-y-4">
              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Emotional Delivery Tone</label>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.emotional_tone}
                  onChange={e => setStudioParams({...studioParams, emotional_tone: e.target.value})}
                >
                  <option value="inspiring">Inspiring / Empowering</option>
                  <option value="shocking">Shocking / Contrarian</option>
                  <option value="curious">Curious / Mystery</option>
                  <option value="urgent">Urgent / Time-Sensitive</option>
                  <option value="empathetic">Empathetic / Vulnerable</option>
                </select>
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Target Distribution Platform</label>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.target_platform}
                  onChange={e => setStudioParams({...studioParams, target_platform: e.target.value})}
                >
                  <option value="youtube_shorts">YouTube Shorts</option>
                  <option value="tiktok">TikTok</option>
                  <option value="instagram_reels">Instagram Reels</option>
                  <option value="all">Cross-Platform (All)</option>
                </select>
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Trend Context / Current Event (Optional)</label>
                <input 
                  type="text" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400/20 outline-none transition-all"
                  value={studioParams.trend_context} 
                  onChange={e => setStudioParams({...studioParams, trend_context: e.target.value})}
                  placeholder="E.g. Apple Vision Pro launch, AI debates"
                />
              </div>
            </div>

            {/* Audio & Narration */}
            <div className="space-y-4">
              <div className="form-group flex flex-col gap-2">
                <div className="flex items-center justify-between gap-4">
                  <label className="form-label text-xs font-semibold text-zinc-300">Narrator Voice</label>
                  <button 
                    type="button" 
                    onClick={handlePreviewVoice}
                    className="btn btn-secondary px-2 py-0.5 text-[9px] flex items-center gap-1 bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10 transition-all"
                    disabled={isPreviewingVoice}
                  >
                    {isPreviewingVoice ? 'Generating...' : '🔊 Preview'}
                  </button>
                </div>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.voice_name}
                  onChange={e => setStudioParams({...studioParams, voice_name: e.target.value})}
                >
                  <optgroup label="Free Narrators (Edge TTS)" className="bg-zinc-950 text-zinc-200">
                    <option value="en-US-AndrewNeural">English Male - Andrew</option>
                    <option value="en-US-EmmaNeural">English Female - Emma</option>
                    <option value="en-US-AvaNeural">English Female - Ava</option>
                    <option value="en-GB-SoniaNeural">British Female - Sonia</option>
                    <option value="en-US-BrianNeural">English Male - Brian</option>
                    <option value="hi-IN-SwaraNeural">Hindi Female - Swara (स्वरा)</option>
                    <option value="hi-IN-MadhurNeural">Hindi Male - Madhur (मधुर)</option>
                  </optgroup>
                  
                  <optgroup label="Premium Multilingual (Google Gemini)" className="bg-zinc-950 text-zinc-200">
                    <option value="gemini:Zephyr-Male">Gemini Male - Zephyr</option>
                    <option value="gemini:Puck-Male">Gemini Male - Puck</option>
                    <option value="gemini:Charon-Male">Gemini Male - Charon</option>
                    <option value="gemini:Kore-Female">Gemini Female - Kore</option>
                    <option value="gemini:Aoede-Female">Gemini Female - Aoede</option>
                    <option value="gemini:Leda-Female">Gemini Female - Leda</option>
                  </optgroup>
                  
                  <optgroup label="Azure Premium" className="bg-zinc-950 text-zinc-200">
                    <option value="hi-IN-AaravNeural">Hindi Male - Aarav (आरव)</option>
                    <option value="hi-IN-AnanyaNeural">Hindi Female - Ananya (अनन्या)</option>
                    <option value="hi-IN-KavyanjaliNeural">Hindi Female - Kavyanjali (काव्यांजलि)</option>
                    <option value="hi-IN-NiharikaNeural">Hindi Female - Niharika (निहारिका)</option>
                    <option value="hi-IN-KavyaNeural">Hindi Female - Kavya (काव्या)</option>
                    <option value="hi-IN-KunalNeural">Hindi Male - Kunal (कुणाल)</option>
                    <option value="hi-IN-RehaanNeural">Hindi Male - Rehaan (रेहान)</option>
                    <option value="hi-IN-AartiNeural">Hindi Female - Aarti (आरती)</option>
                    <option value="hi-IN-ArjunNeural">Hindi Male - Arjun (अर्जुन)</option>
                  </optgroup>

                  <optgroup label="Sarvam AI Premium" className="bg-zinc-950 text-zinc-200">
                    <option value="sarvam:shubh">Sarvam Hindi Male - Shubh</option>
                    <option value="sarvam:aditya">Sarvam Hindi Male - Aditya</option>
                    <option value="sarvam:ritu">Sarvam Hindi Female - Ritu</option>
                    <option value="sarvam:priya">Sarvam Hindi Female - Priya</option>
                    <option value="sarvam:meera">Sarvam Hindi Female - Meera</option>
                  </optgroup>
                </select>
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Background Music</label>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.bgm_file}
                  onChange={e => setStudioParams({...studioParams, bgm_file: e.target.value})}
                >
                  <option value="">Random Background Song</option>
                  {bgmFiles.map(bgm => (
                    <option key={bgm.name} value={bgm.name}>{bgm.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Voice Accent Language</label>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.video_language}
                  onChange={e => setStudioParams({...studioParams, video_language: e.target.value})}
                >
                  <option value="">Detect Automatically</option>
                  <option value="en">English (en)</option>
                  <option value="hi">Hindi (hi)</option>
                </select>
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Target Duration</label>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.video_duration}
                  onChange={e => setStudioParams({...studioParams, video_duration: parseInt(e.target.value)})}
                >
                  <option value={15}>15 Seconds (Short/Punchy)</option>
                  <option value={30}>30 Seconds (Medium/Reels)</option>
                  <option value={60}>60 Seconds (Full Short/TikTok)</option>
                  <option value={90}>90 Seconds (1:30 Mins)</option>
                  <option value={120}>120 Seconds (2:00 Mins)</option>
                  <option value={180}>180 Seconds (3:00 Mins)</option>
                </select>
              </div>
            </div>

            {/* Layout & Subtitles */}
            <div className="space-y-4 border-t border-white/5 pt-4">
              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Aspect Ratio</label>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.video_aspect}
                  onChange={e => setStudioParams({...studioParams, video_aspect: e.target.value})}
                >
                  <option value="9:16">Portrait 9:16</option>
                  <option value="16:9">Landscape 16:9</option>
                  <option value="1:1">Square 1:1</option>
                </select>
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Clip Duration (sec)</label>
                <input 
                  type="number" 
                  className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400/20 outline-none transition-all"
                  min="2" 
                  max="10"
                  value={studioParams.video_clip_duration}
                  onChange={e => setStudioParams({...studioParams, video_clip_duration: parseInt(e.target.value)})}
                />
              </div>

              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Font Face Name</label>
                <select 
                  className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  value={studioParams.font_name}
                  onChange={e => setStudioParams({...studioParams, font_name: e.target.value})}
                >
                  <option value="Poppins-Bold.ttf">Poppins Bold</option>
                  <option value="BebasNeue-Regular.ttf">Bebas Neue Regular</option>
                  <option value="Montserrat-ExtraBold.ttf">Montserrat ExtraBold</option>
                  <option value="Charm-Bold.ttf">Charm Bold</option>
                  <option value="MicrosoftYaHeiBold.ttc">Microsoft YaHei</option>
                </select>
              </div>
            </div>

            <div className="space-y-4">
              <div className="form-group flex flex-col gap-2">
                <label className="form-label text-xs font-semibold text-zinc-300">Font Foreground Color</label>
                <input 
                  type="color" 
                  className="form-control border border-white/5 rounded-xl h-10 p-1 bg-black/40 cursor-pointer"
                  value={studioParams.text_fore_color}
                  onChange={e => setStudioParams({...studioParams, text_fore_color: e.target.value})}
                />
              </div>

              <div className="form-group flex items-center gap-3 pt-2">
                <input 
                  type="checkbox" 
                  id="text_background_color"
                  checked={studioParams.text_background_color}
                  onChange={e => setStudioParams({...studioParams, text_background_color: e.target.checked})}
                  className="w-4 h-4 rounded bg-zinc-900 border-white/10 text-yellow-400 focus:ring-yellow-400/20 cursor-pointer"
                />
                <label htmlFor="text_background_color" className="cursor-pointer text-xs text-zinc-400 select-none hover:text-zinc-300">
                  Add background box behind captions
                </label>
              </div>

              {/* Viral Effects */}
              <div className="space-y-4 border-t border-white/5 pt-4">
                <h4 className="text-xs font-bold text-zinc-300 flex items-center gap-1.5">
                  <Sparkles size={14} className="text-yellow-400" />
                  Viral Visual & Audio Effects
                </h4>

                {/* Toggle Chips */}
                <div className="flex flex-wrap gap-2">
                  <button
                    key="kb"
                    type="button"
                    onClick={() => setStudioParams({ ...studioParams, ken_burns: !studioParams.ken_burns })}
                    className={`py-1.5 px-3 rounded-xl font-bold text-[10px] border transition-all ${
                      studioParams.ken_burns
                        ? 'bg-yellow-400/10 border-yellow-400/30 text-yellow-400'
                        : 'bg-zinc-950/40 border-white/5 text-zinc-400 hover:text-zinc-300'
                    }`}
                  >
                    Ken Burns Zoom
                  </button>
                  <button
                    key="bs"
                    type="button"
                    onClick={() => setStudioParams({ ...studioParams, beat_sync: !studioParams.beat_sync })}
                    className={`py-1.5 px-3 rounded-xl font-bold text-[10px] border transition-all ${
                      studioParams.beat_sync
                        ? 'bg-yellow-400/10 border-yellow-400/30 text-yellow-400'
                        : 'bg-zinc-950/40 border-white/5 text-zinc-400 hover:text-zinc-300'
                    }`}
                  >
                    Beat-Sync Cuts
                  </button>
                  <button
                    key="es"
                    type="button"
                    onClick={() => setStudioParams({ ...studioParams, emoji_subtitles: !studioParams.emoji_subtitles })}
                    className={`py-1.5 px-3 rounded-xl font-bold text-[10px] border transition-all ${
                      studioParams.emoji_subtitles
                        ? 'bg-yellow-400/10 border-yellow-400/30 text-yellow-400'
                        : 'bg-zinc-950/40 border-white/5 text-zinc-400 hover:text-zinc-300'
                    }`}
                  >
                    Emoji Subtitles
                  </button>
                </div>

                {/* Color Grade Dropdown */}
                <div className="form-group flex flex-col gap-2">
                  <label className="form-label text-xs font-semibold text-zinc-300">Color Grade Preset</label>
                  <select 
                    className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                    value={studioParams.color_grade_preset}
                    onChange={e => setStudioParams({...studioParams, color_grade_preset: e.target.value})}
                  >
                    <option value="none">None</option>
                    <option value="warm">Cinematic Warm</option>
                    <option value="cool">Cool Blue</option>
                    <option value="dramatic">Dramatic Dark</option>
                  </select>
                </div>

                {/* Subtitle Animation Dropdown */}
                <div className="form-group flex flex-col gap-2">
                  <label className="form-label text-xs font-semibold text-zinc-300">Subtitle Animation</label>
                  <select 
                    className="form-control bg-zinc-900 border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                    value={studioParams.subtitle_animation}
                    onChange={e => setStudioParams({...studioParams, subtitle_animation: e.target.value})}
                  >
                    <option value="static">Static</option>
                    <option value="pop">Pop</option>
                    <option value="slide_up">Slide Up</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Submit Actions */}
            {!studioParams.video_subject.trim() && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs font-medium flex items-center gap-2">
                <AlertTriangle size={14} className="flex-shrink-0" />
                Please enter a Video Subject / Theme above before generating.
              </div>
            )}
            <div className="pt-4 border-t border-white/5 flex gap-4">
              <button 
                type="button"
                onClick={(e) => {
                  if (!studioParams.video_subject.trim()) {
                    alert('Please enter a Video Subject / Theme first!');
                    return;
                  }
                  handleGenerateVideo(e);
                }}
                className="btn btn-primary px-6 py-3 rounded-xl font-bold flex items-center gap-2 text-sm shadow-lg shadow-yellow-500/10 active:scale-95 transition-all w-full justify-center" 
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin" size={16} /> Rendering Task...
                  </>
                ) : (
                  <>
                    <Sparkles size={16} /> Stitch &amp; Cloud Upload
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Middle Column: AI Script Developer Panel & Analytics */}
        <div className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-6 space-y-6">
            <h3 className="text-base font-bold border-b border-white/5 pb-3 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Brain size={16} className="text-purple-400" />
                AI Script Developer
              </span>
              {studioParams.video_script && (
                <span className="text-[9px] bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 rounded-full font-bold uppercase">
                  Draft Loaded
                </span>
              )}
            </h3>

            {/* Live Textarea */}
            <div className="form-group flex flex-col gap-2">
              <label className="form-label text-xs font-semibold text-zinc-300 flex items-center justify-between">
                <span>Narrator Script Text</span>
                <span className="text-[10px] text-zinc-500 font-medium">
                  {studioParams.video_script ? `${studioParams.video_script.length} chars` : 'Empty'}
                </span>
              </label>
              <textarea 
                className="form-control bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400/20 outline-none transition-all text-xs h-64 resize-none leading-relaxed font-mono"
                value={studioParams.video_script} 
                onChange={e => setStudioParams({...studioParams, video_script: e.target.value})}
                placeholder="Click 'Draft with AI' to build a custom narrative script dynamically, or type your own video script directly here..."
              />
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-3">
              <button 
                type="button"
                onClick={handleDraftScript}
                disabled={isGeneratingScript || isScoringScript}
                className="btn btn-secondary px-4 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 bg-purple-500/10 border-purple-500/20 hover:bg-purple-500/20 hover:border-purple-500/30 text-purple-300 disabled:opacity-50 transition-all active:scale-95"
              >
                {isGeneratingScript ? (
                  <>
                    <Loader2 className="animate-spin" size={14} /> Drafting...
                  </>
                ) : (
                  <>
                    <Sparkles size={14} /> Draft with AI
                  </>
                )}
              </button>

              <button 
                type="button"
                onClick={handleScoreScript}
                disabled={!studioParams.video_script || isGeneratingScript || isScoringScript}
                className="btn btn-secondary px-4 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 bg-amber-500/10 border-amber-500/20 hover:bg-amber-500/20 hover:border-amber-500/30 text-amber-300 disabled:opacity-50 transition-all active:scale-95"
              >
                {isScoringScript ? (
                  <>
                    <Loader2 className="animate-spin" size={14} /> Evaluating...
                  </>
                ) : (
                  <>
                    <BarChart2 size={14} /> Analyze & Score
                  </>
                )}
              </button>
            </div>

            {scoreError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 flex items-center gap-2">
                <AlertTriangle size={14} className="flex-shrink-0" />
                <span>{scoreError}</span>
              </div>
            )}

            {/* Virality Analytics Scorecard */}
            {score && (
              <div className="space-y-5 border-t border-white/5 pt-5 animate-fade-in">
                <h4 className="text-xs font-bold text-zinc-300 flex items-center gap-1.5">
                  <BarChart2 size={14} className="text-amber-400" />
                  Virality Potential Analytics
                </h4>

                {/* Overall Score Badge */}
                <div className="flex items-center gap-5 bg-zinc-900/50 border border-white/5 p-4 rounded-xl">
                  <div className="relative flex-shrink-0 flex items-center justify-center w-14 h-14 rounded-full bg-zinc-950 border-4 border-yellow-500/20 shadow-inner">
                    <div className="absolute inset-0 rounded-full bg-yellow-500/10 animate-ping opacity-25" />
                    <span className="text-base font-black text-yellow-400">{score.overall_score}%</span>
                  </div>
                  <div>
                    <h5 className="font-extrabold text-xs text-zinc-200">Virality Rating</h5>
                    <p className="text-[10px] text-zinc-400 leading-normal mt-0.5">
                      This script has been parsed against hook metrics and retention curves.
                    </p>
                  </div>
                </div>

                {/* Progress bars */}
                <div className="space-y-3 bg-zinc-900/20 border border-white/5 p-4 rounded-xl">
                  <MetricBar name="Hook Potential" score={score.hook_score} color="from-amber-500 to-orange-500" />
                  <MetricBar name="Emotional Delivery" score={score.emotion_score} color="from-rose-500 to-red-500" />
                  <MetricBar name="Clarity & Retention" score={score.clarity_score} color="from-emerald-500 to-teal-500" />
                  <MetricBar name="Pacing & Flow" score={score.pacing_score} color="from-blue-500 to-indigo-500" />
                  <MetricBar name="Call to Action / Loop" score={score.cta_score} color="from-purple-500 to-fuchsia-500" />
                </div>

                {/* Actionable Suggestion */}
                <div className="p-4 bg-zinc-900/60 border-l-4 border-yellow-500 rounded-r-xl space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-yellow-400">
                    <Lightbulb size={14} />
                    <span>AI Improvement Tip</span>
                  </div>
                  <p className="text-[11px] text-zinc-300 leading-relaxed italic">
                    "{score.improvement_tip}"
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: 🔥 Trending Now Sidebar Panel */}
        <div className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-6 space-y-6">
            <h3 className="text-base font-bold border-b border-white/5 pb-3 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Flame size={16} className="text-orange-500 animate-pulse" />
                Trending Now
              </span>
              <button 
                type="button" 
                onClick={handleRefreshTrends}
                className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-all"
                disabled={isFetchingTrends}
                title="Refresh Topics"
              >
                <RefreshCw size={12} className={`${isFetchingTrends ? 'animate-spin text-orange-400' : 'text-zinc-400'}`} />
              </button>
            </h3>

            {/* Platform Selector Tabs */}
            <div className="grid grid-cols-2 gap-2 bg-black/40 p-1 rounded-xl border border-white/5">
              <button
                type="button"
                onClick={() => setActivePlatform('google')}
                className={`py-1.5 px-3 rounded-lg font-bold text-[11px] flex items-center justify-center gap-1.5 transition-all ${
                  activePlatform === 'google'
                    ? 'bg-zinc-800 text-white shadow-md'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Globe size={12} />
                Google Search
              </button>
              <button
                type="button"
                onClick={() => setActivePlatform('youtube')}
                className={`py-1.5 px-3 rounded-lg font-bold text-[11px] flex items-center justify-center gap-1.5 transition-all ${
                  activePlatform === 'youtube'
                    ? 'bg-zinc-800 text-white shadow-md'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Youtube size={12} />
                YouTube Viral
              </button>
            </div>

            {/* Category Filter Pills (Horizontal Scroll) */}
            <div className="flex gap-1.5 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-zinc-800">
              {CATEGORIES.map(cat => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setActiveCategory(cat.id)}
                  className={`py-1 px-2.5 rounded-full text-[10px] font-bold border transition-all whitespace-nowrap ${
                    activeCategory === cat.id
                      ? 'bg-yellow-400/10 border-yellow-400/30 text-yellow-400'
                      : 'bg-zinc-900/40 border-white/5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/70'
                  }`}
                >
                  {cat.name}
                </button>
              ))}
            </div>

            {/* Trends List */}
            {isFetchingTrends ? (
              <div className="flex flex-col items-center justify-center py-12 text-zinc-500 gap-2">
                <Loader2 className="animate-spin text-orange-500" size={20} />
                <span className="text-xs">Fetching hot search metrics...</span>
              </div>
            ) : trends.length === 0 ? (
              <div className="text-center py-12 text-zinc-500 text-xs">
                No trends found. Click refresh to retry.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-zinc-800">
                {trends.map((trend, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSelectTrend(trend.topic)}
                    className="group relative bg-zinc-950/40 hover:bg-zinc-900/40 border border-white/5 hover:border-yellow-500/20 p-3 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-3"
                    title="Click to auto-fill Video Subject"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="text-xs font-bold text-zinc-500 w-4 flex-shrink-0">
                        {idx + 1}
                      </span>
                      <span className="text-orange-500 flex-shrink-0 text-xs">🔥</span>
                      <span className="text-xs font-semibold text-zinc-200 truncate group-hover:text-yellow-400 transition-colors">
                        {trend.topic}
                      </span>
                    </div>
                    {trend.score && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 flex-shrink-0">
                        {trend.score}
                      </span>
                    )}

                    {/* Suggested Hook Tooltip */}
                    {trend.suggested_hook && (
                      <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-64 bg-zinc-900 border border-white/10 p-3 rounded-xl shadow-2xl text-[11px] text-zinc-300 z-[100] pointer-events-none">
                        <div className="flex items-center gap-1 text-[10px] font-bold text-yellow-400 mb-1">
                          <Lightbulb size={12} />
                          <span>Suggested Hook</span>
                        </div>
                        <p className="leading-relaxed italic">"{trend.suggested_hook}"</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            <div className="bg-zinc-900/30 border border-white/5 p-3 rounded-xl flex gap-2">
              <Lightbulb size={14} className="text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-[10px] text-zinc-500 leading-normal">
                Click any trending topic to instantly fill the theme subject. Hover over topics to preview AI hook suggestions.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
