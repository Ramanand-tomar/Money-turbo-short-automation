import React from 'react';
import { 
  Tv, 
  Video, 
  Database, 
  Clock, 
  Activity, 
  Cpu, 
  Cloud,
  X,
  Menu,
  Shield,
  Share2
} from 'lucide-react';
import { UserButton } from '@clerk/clerk-react';

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

const FolderPlay = ({ size = 20, ...props }) => (
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
    <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    <polygon points="10 9 15 12 10 15" fill="currentColor" />
  </svg>
);

export default function Sidebar({ activeTab, setActiveTab, user, sidebarOpen, setSidebarOpen, isAdmin }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Tv },
    { id: 'studio', label: 'Video Studio', icon: Video },
    { id: 'settings', label: 'Settings & APIs', icon: Database },
    { id: 'publish', label: 'Publishing Hub', icon: Share2 },
    { id: 'library', label: 'Video Library', icon: FolderPlay },
  ];

  if (isAdmin) {
    navItems.push({ id: 'admin', label: 'Admin Panel', icon: Shield });
  }

  return (
    <>
      {/* Mobile Top Bar (Only visible on screens smaller than md) */}
      <header className="md:hidden flex items-center justify-between px-6 py-4 bg-zinc-950/80 border-b border-white/5 backdrop-blur-md sticky top-0 z-[60]">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-yellow-400 to-orange-500 w-8 h-8 rounded-lg flex items-center justify-center text-black font-extrabold text-sm shadow-lg shadow-yellow-500/10">🎬</div>
          <span className="text-lg font-bold bg-gradient-to-r from-white to-zinc-300 bg-clip-text text-transparent">Turbo Studio</span>
        </div>
        <button 
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 text-zinc-400 hover:text-white transition-colors"
        >
          <Menu size={24} />
        </button>
      </header>

      {/* Backdrop overlay for mobile drawer */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)}
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-[90] transition-opacity duration-300"
        />
      )}

      {/* Sidebar drawer container */}
      <aside className={`
        fixed top-0 bottom-0 left-0 w-[280px] bg-zinc-950/95 border-r border-white/5 p-6 z-[100]
        flex flex-col transition-transform duration-300 ease-in-out md:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo and close button inside side drawer */}
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-yellow-400 to-orange-500 w-10 h-10 rounded-lg flex items-center justify-center text-black font-extrabold text-xl shadow-lg shadow-yellow-500/10">🎬</div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-white to-zinc-200 bg-clip-text text-transparent">Turbo Studio</h1>
          </div>
          <button 
            onClick={() => setSidebarOpen(false)}
            className="md:hidden p-2 text-zinc-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation links */}
        <nav className="flex flex-col gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setSidebarOpen(false);
                }}
                className={`
                  flex items-center gap-4.5 px-4.5 py-3.5 rounded-xl font-medium transition-all duration-200 text-left border border-transparent
                  ${isActive 
                    ? 'bg-yellow-400 text-black font-semibold shadow-lg shadow-yellow-400/10' 
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/3'}
                `}
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Bottom Connection Status Metrics */}
        <div className="mt-auto pt-6 border-t border-white/5 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <Cpu size={14} className="text-yellow-400" />
            <span>NeonDB: Connected</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <Cloud size={14} className="text-emerald-400" />
            <span>Cloudinary CDN: Active</span>
          </div>
          
          {/* User profile widget */}
          <div className="flex items-center gap-3.5 pt-4 border-t border-white/5 border-dashed">
            <UserButton afterSignOutUrl="/" showName={false} appearance={{
              elements: {
                userButtonAvatarBox: 'user-avatar-clerk'
              }
            }} />
            <div className="flex flex-col overflow-hidden">
              <span className="text-sm font-semibold text-zinc-200 truncate leading-tight">
                {user?.fullName || user?.username || 'SaaS User'}
              </span>
              <span className="text-xs text-zinc-500 truncate leading-tight">
                {user?.primaryEmailAddress?.emailAddress || 'active account'}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
