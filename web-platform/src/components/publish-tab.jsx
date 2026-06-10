import React from 'react';
import { 
  Loader2, 
  Link, 
  Link2Off, 
  FileCode, 
  Info, 
  Calendar, 
  CheckCircle, 
  Clock, 
  XCircle, 
  Trash2,
  AlertTriangle,
  Play
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

export default function PublishTab({
  youtubeStatus,
  tiktokStatus,
  instagramStatus,
  handleConnectYoutube,
  handleDisconnectYoutube,
  handleConnectTiktok,
  handleDisconnectTiktok,
  handleConnectInstagram,
  handleDisconnectInstagram,
  clientSecretFile,
  setClientSecretFile,
  isUploadingSecret,
  handleUploadClientSecret,
  scheduledPosts,
  handleCancelSchedule,
  isLoadingSchedule,
  fetchScheduledPosts
}) {
  const [activePlatformTab, setActivePlatformTab] = React.useState('youtube');

  return (
    <div className="space-y-8 animate-fade-in">
      <header className="page-header">
        <h2 className="page-title text-2xl md:text-3xl font-extrabold">Multi-Platform Publishing Hub</h2>
        <p className="page-subtitle text-zinc-400 text-sm md:text-base">Link accounts and schedule timed posts to automate viral short-video publishing on autopilot.</p>
      </header>

      {/* Integration Panels Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Connection Management Column */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-panel p-6 flex flex-col gap-4">
            <h3 className="text-base font-bold text-zinc-200">Account Connections</h3>
            <p className="text-xs text-zinc-400">Authenticate your social channels to unlock publishing operations.</p>
            
            <div className="flex flex-col gap-3.5 mt-2">
              
              {/* YouTube connection item */}
              <button 
                onClick={() => setActivePlatformTab('youtube')}
                className={`flex items-center justify-between p-4.5 rounded-xl border text-left transition-all ${
                  activePlatformTab === 'youtube' 
                    ? 'bg-yellow-400/5 border-yellow-400/40 text-yellow-400' 
                    : 'bg-zinc-950/20 border-white/5 text-zinc-400 hover:border-white/10 hover:text-zinc-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-500/10 text-red-500 rounded-lg flex items-center justify-center">
                    <Youtube size={18} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-zinc-200">YouTube Shorts</div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">
                      {youtubeStatus.channel_connected ? youtubeStatus.channel_name : 'Not connected'}
                    </div>
                  </div>
                </div>
                <div className={`w-2.5 h-2.5 rounded-full ${youtubeStatus.channel_connected ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
              </button>

              {/* TikTok connection item */}
              <button 
                onClick={() => setActivePlatformTab('tiktok')}
                className={`flex items-center justify-between p-4.5 rounded-xl border text-left transition-all ${
                  activePlatformTab === 'tiktok' 
                    ? 'bg-yellow-400/5 border-yellow-400/40 text-yellow-400' 
                    : 'bg-zinc-950/20 border-white/5 text-zinc-400 hover:border-white/10 hover:text-zinc-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-teal-500/10 text-teal-400 rounded-lg flex items-center justify-center">
                    <Tiktok size={18} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-zinc-200">TikTok Shorts</div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">
                      {tiktokStatus?.channel_connected ? tiktokStatus.channel_name : 'Not connected'}
                    </div>
                  </div>
                </div>
                <div className={`w-2.5 h-2.5 rounded-full ${tiktokStatus?.channel_connected ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
              </button>

              {/* Instagram Reels connection item */}
              <button 
                onClick={() => setActivePlatformTab('instagram')}
                className={`flex items-center justify-between p-4.5 rounded-xl border text-left transition-all ${
                  activePlatformTab === 'instagram' 
                    ? 'bg-yellow-400/5 border-yellow-400/40 text-yellow-400' 
                    : 'bg-zinc-950/20 border-white/5 text-zinc-400 hover:border-white/10 hover:text-zinc-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-pink-500/10 text-pink-400 rounded-lg flex items-center justify-center">
                    <Instagram size={18} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-zinc-200">Instagram Reels</div>
                    <div className="text-[10px] text-zinc-500 mt-0.5">
                      {instagramStatus?.channel_connected ? instagramStatus.channel_name : 'Not connected'}
                    </div>
                  </div>
                </div>
                <div className={`w-2.5 h-2.5 rounded-full ${instagramStatus?.channel_connected ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
              </button>

            </div>
          </div>
        </div>

        {/* Detailed Config Section Column */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* YouTube Settings Tab */}
          {activePlatformTab === 'youtube' && (
            <div className="glass-panel p-6 md:p-8 space-y-6">
              <div className="flex items-center gap-4 border-b border-white/5 pb-5">
                <div className="bg-red-500/10 text-red-500 w-12 h-12 rounded-xl flex items-center justify-center">
                  <Youtube size={28} />
                </div>
                <div>
                  <h3 className="text-base md:text-lg font-bold text-zinc-100">YouTube Channel Setup</h3>
                  <p className="text-xs text-zinc-400">Directly sync and publish automated vertical shorts to your YouTube account.</p>
                </div>
              </div>

              <div className="p-5 bg-white/[0.01] border border-white/5 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="font-bold text-sm text-zinc-200">Status</div>
                  <div className="text-xs text-zinc-400 mt-1">
                    {youtubeStatus.channel_connected 
                      ? `Connected to: ${youtubeStatus.channel_name}` 
                      : 'Not connected. Connect using Google credentials.'}
                  </div>
                </div>
                <div>
                  {youtubeStatus.channel_connected ? (
                    <button 
                      onClick={handleDisconnectYoutube}
                      className="btn btn-secondary text-xs px-4 py-2 flex items-center gap-1.5 text-red-400 hover:text-red-300 border-red-500/10 hover:border-red-500/20 bg-red-500/5"
                    >
                      <Link2Off size={14} /> Disconnect Channel
                    </button>
                  ) : (
                    youtubeStatus.client_secret_exists && (
                      <button 
                        onClick={handleConnectYoutube}
                        className="btn btn-primary text-xs px-5 py-2.5 flex items-center gap-1.5 text-black font-bold active:scale-95"
                      >
                        <Link size={14} /> Connect YouTube Channel
                      </button>
                    )
                  )}
                </div>
              </div>

              {!youtubeStatus.channel_connected && (
                <div className="space-y-4 border-t border-white/5 pt-6">
                  <h4 className="font-bold text-sm text-zinc-200 flex items-center gap-2">
                    <FileCode size={18} className="text-yellow-400" />
                    {youtubeStatus.client_secret_exists ? 'Upload New Client Secret JSON' : 'Upload Client Secret JSON'}
                  </h4>

                  {youtubeStatus.client_secret_exists && (
                    <p className="text-xs text-zinc-400">
                      A client secret is already configured. You can upload another JSON file to overwrite it.
                    </p>
                  )}

                  <form onSubmit={handleUploadClientSecret} className="space-y-4">
                    <input 
                      type="file" 
                      accept=".json"
                      onChange={e => setClientSecretFile(e.target.files[0])}
                      className="block w-full text-xs text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700 file:cursor-pointer"
                    />
                    <button 
                      type="submit" 
                      className="btn btn-secondary text-xs px-4 py-2"
                      disabled={isUploadingSecret || !clientSecretFile}
                    >
                      {isUploadingSecret ? 'Uploading...' : 'Upload client_secret.json'}
                    </button>
                  </form>

                  <div className="p-4 bg-yellow-500/[0.02] border border-yellow-500/10 rounded-xl flex gap-3 text-xs text-zinc-400 leading-relaxed">
                    <Info size={16} className="text-yellow-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <strong className="block text-yellow-400 mb-1">Developer Credentials Warning</strong>
                      Google requires client credentials configuration to authenticate your channel. Download <code>client_secret.json</code> from the Google Cloud Console and upload it.
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TikTok Settings Tab */}
          {activePlatformTab === 'tiktok' && (
            <div className="glass-panel p-6 md:p-8 space-y-6">
              <div className="flex items-center gap-4 border-b border-white/5 pb-5">
                <div className="bg-teal-500/10 text-teal-400 w-12 h-12 rounded-xl flex items-center justify-center">
                  <Tiktok size={24} />
                </div>
                <div>
                  <h3 className="text-base md:text-lg font-bold text-zinc-100">TikTok API Connection</h3>
                  <p className="text-xs text-zinc-400">Cross-post your short videos directly to TikTok using the secure Posting API v2.</p>
                </div>
              </div>

              <div className="p-5 bg-white/[0.01] border border-white/5 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="font-bold text-sm text-zinc-200">Status</div>
                  <div className="text-xs text-zinc-400 mt-1">
                    {tiktokStatus?.channel_connected 
                      ? `Connected to profile: ${tiktokStatus.channel_name}` 
                      : 'No TikTok account linked.'}
                  </div>
                </div>
                <div>
                  {tiktokStatus?.channel_connected ? (
                    <button 
                      onClick={handleDisconnectTiktok}
                      className="btn btn-secondary text-xs px-4 py-2 flex items-center gap-1.5 text-red-400 hover:text-red-300 border-red-500/10 hover:border-red-500/20 bg-red-500/5"
                    >
                      <Link2Off size={14} /> Disconnect Account
                    </button>
                  ) : (
                    <button 
                      onClick={handleConnectTiktok}
                      className="btn btn-primary text-xs px-5 py-2.5 flex items-center gap-1.5 text-black font-bold active:scale-95 bg-teal-400 hover:bg-teal-500"
                    >
                      <Link size={14} /> Connect TikTok Account
                    </button>
                  )}
                </div>
              </div>

              <div className="p-4 bg-teal-500/[0.02] border border-teal-500/10 rounded-xl flex gap-3 text-xs text-zinc-400 leading-relaxed">
                <Info size={16} className="text-teal-400 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="block text-teal-400 mb-1">Authorization Details</strong>
                  The connection will grant the platform permission to publish videos directly to your feed. Private setting uploads are supported but will default to public publishing.
                </div>
              </div>
            </div>
          )}

          {/* Instagram Settings Tab */}
          {activePlatformTab === 'instagram' && (
            <div className="glass-panel p-6 md:p-8 space-y-6">
              <div className="flex items-center gap-4 border-b border-white/5 pb-5">
                <div className="bg-pink-500/10 text-pink-400 w-12 h-12 rounded-xl flex items-center justify-center">
                  <Instagram size={24} />
                </div>
                <div>
                  <h3 className="text-base md:text-lg font-bold text-zinc-100">Instagram Reels Publishing</h3>
                  <p className="text-xs text-zinc-400">Stitch and upload compiled videos as Instagram Reels using the Facebook Graph API.</p>
                </div>
              </div>

              <div className="p-5 bg-white/[0.01] border border-white/5 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="font-bold text-sm text-zinc-200">Status</div>
                  <div className="text-xs text-zinc-400 mt-1">
                    {instagramStatus?.channel_connected 
                      ? `Connected Business Profile: ${instagramStatus.channel_name}` 
                      : 'No Instagram account connected.'}
                  </div>
                </div>
                <div>
                  {instagramStatus?.channel_connected ? (
                    <button 
                      onClick={handleDisconnectInstagram}
                      className="btn btn-secondary text-xs px-4 py-2 flex items-center gap-1.5 text-red-400 hover:text-red-300 border-red-500/10 hover:border-red-500/20 bg-red-500/5"
                    >
                      <Link2Off size={14} /> Disconnect Account
                    </button>
                  ) : (
                    <button 
                      onClick={handleConnectInstagram}
                      className="btn btn-primary text-xs px-5 py-2.5 flex items-center gap-1.5 text-black font-bold active:scale-95 bg-pink-400 hover:bg-pink-500"
                    >
                      <Link size={14} /> Connect Instagram Account
                    </button>
                  )}
                </div>
              </div>

              <div className="p-4 bg-pink-500/[0.02] border border-pink-500/10 rounded-xl flex gap-3 text-xs text-zinc-400 leading-relaxed">
                <Info size={16} className="text-pink-400 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="block text-pink-400 mb-1">Instagram Business Account Requirement</strong>
                  Instagram Graph API publishing requires a Professional/Business Instagram Account linked to a Facebook Page. Standard personal Instagram accounts are not supported by Meta API protocols.
                </div>
              </div>
            </div>
          )}

        </div>

      </div>

      {/* Scheduled Queue Section */}
      <div className="glass-panel p-6">
        <div className="flex items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-base md:text-lg font-bold text-zinc-100 flex items-center gap-2">
              <Calendar size={20} className="text-yellow-400" />
              Automated Posting Scheduler Ledger
            </h3>
            <p className="text-xs text-zinc-400 mt-1">Check pending, published, and failed scheduled publishing events.</p>
          </div>
          <button 
            onClick={fetchScheduledPosts} 
            className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1"
            disabled={isLoadingSchedule}
          >
            Refresh Queue
          </button>
        </div>

        <div className="overflow-x-auto">
          {isLoadingSchedule ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-zinc-400">
              <Loader2 className="animate-spin text-yellow-400" size={24} />
              <span className="text-sm">Fetching scheduled publishing queue...</span>
            </div>
          ) : !scheduledPosts || scheduledPosts.length === 0 ? (
            <div className="py-12 text-center text-zinc-500 text-sm">
              No scheduled posts listed in NeonDB. Schedule a video from the Video Library tab!
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs md:text-sm">
              <thead>
                <tr className="border-b border-white/5 text-zinc-400">
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[10px]">Video Subject</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[10px]">Platform</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[10px]">Scheduled Time</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[10px]">Publish Status</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[10px]">Platform Reference / Error</th>
                  <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[10px] text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {scheduledPosts.map((post) => {
                  let statusBadge = null;
                  if (post.status === 'pending') {
                    statusBadge = (
                      <span className="px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 flex items-center gap-1 w-max">
                        <Clock size={11} /> Pending
                      </span>
                    );
                  } else if (post.status === 'publishing') {
                    statusBadge = (
                      <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1 w-max">
                        <Loader2 className="animate-spin" size={11} /> Uploading...
                      </span>
                    );
                  } else if (post.status === 'published') {
                    statusBadge = (
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1 w-max">
                        <CheckCircle size={11} /> Published
                      </span>
                    );
                  } else {
                    statusBadge = (
                      <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 flex items-center gap-1 w-max">
                        <XCircle size={11} /> Failed
                      </span>
                    );
                  }

                  let responseText = "-";
                  if (post.result) {
                    try {
                      const resParsed = JSON.parse(post.result);
                      if (resParsed.error) {
                        responseText = resParsed.error;
                      } else if (resParsed.platform_response) {
                        responseText = `Published successfully (ID: ${resParsed.platform_response.media_id || resParsed.platform_response.publish_id || 'OK'})`;
                      } else {
                        responseText = post.result;
                      }
                    } catch (e) {
                      responseText = post.result;
                    }
                  }

                  return (
                    <tr key={post.id} className="border-b border-white/5 hover:bg-white/[0.01]">
                      <td className="py-3.5 px-4 font-semibold text-zinc-200 max-w-[200px] truncate" title={post.video_subject}>
                        {post.video_subject}
                      </td>
                      <td className="py-3.5 px-4 text-zinc-300 font-medium capitalize flex items-center gap-1.5 mt-1.5 border-0">
                        {post.platform === 'youtube' && <Youtube size={14} className="text-red-500" />}
                        {post.platform === 'tiktok' && <Tiktok size={14} className="text-teal-400" />}
                        {post.platform === 'instagram' && <Instagram size={14} className="text-pink-400" />}
                        {post.platform}
                      </td>
                      <td className="py-3.5 px-4 text-zinc-400 font-mono text-[11px]">
                        {post.scheduled_at.replace('T', ' ')}
                      </td>
                      <td className="py-3.5 px-4">
                        {statusBadge}
                      </td>
                      <td className="py-3.5 px-4 text-zinc-500 max-w-[240px] truncate text-xs" title={responseText}>
                        {responseText}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {post.status === 'pending' && (
                          <button 
                            onClick={() => handleCancelSchedule(post.id)}
                            className="text-red-400 hover:text-red-300 hover:bg-red-500/10 p-1.5 rounded transition-all"
                            title="Cancel Scheduled Post"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

    </div>
  );
}
