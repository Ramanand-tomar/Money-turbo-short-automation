import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Video, 
  Activity, 
  Cloud, 
  Settings, 
  Search, 
  Edit2, 
  Trash2, 
  Play, 
  Pause, 
  Save, 
  X, 
  ChevronLeft, 
  ChevronRight,
  ShieldAlert,
  Loader2,
  Lock
} from 'lucide-react';

export default function AdminTab({ BACKEND_URL, getHeaders, addLog }) {
  const [activeSubTab, setActiveSubTab] = useState('queue');
  const [stats, setStats] = useState({
    total_users: 0,
    total_tasks: 0,
    active_tasks: 0,
    cdn_uploads: 0
  });

  // Tasks states
  const [tasks, setTasks] = useState([]);
  const [tasksTotal, setTasksTotal] = useState(0);
  const [tasksPage, setTasksPage] = useState(1);
  const [tasksPageSize] = useState(20);

  // Users states
  const [usersList, setUsersList] = useState([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersPageSize] = useState(10);
  const [userSearch, setUserSearch] = useState('');
  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({
    email: '',
    role: 'user',
    plan: 'free',
    quota_videos_per_day: 5,
    quota_videos_per_month: 50,
    is_active: true
  });

  // Configurations states
  const [configs, setConfigs] = useState({});
  const [blocklist, setBlocklist] = useState('');
  const [isSavingConfig, setIsSavingConfig] = useState(false);

  // General UI states
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [isUpdatingUser, setIsUpdatingUser] = useState(false);

  const fetchStats = async () => {
    setIsLoadingStats(true);
    try {
      const res = await fetch(`${BACKEND_URL}/admin/stats`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setStats(data.data);
      }
    } catch (e) {
      console.error("Failed to fetch admin stats:", e);
    } finally {
      setIsLoadingStats(false);
    }
  };

  const fetchTasks = async (page = tasksPage) => {
    setIsLoadingTasks(true);
    try {
      const res = await fetch(`${BACKEND_URL}/admin/tasks?page=${page}&page_size=${tasksPageSize}`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setTasks(data.data.tasks || []);
        setTasksTotal(data.data.total || 0);
      }
    } catch (e) {
      console.error("Failed to fetch admin tasks queue:", e);
    } finally {
      setIsLoadingTasks(false);
    }
  };

  const fetchUsers = async (page = usersPage, search = userSearch) => {
    setIsLoadingUsers(true);
    try {
      const queryParams = new URLSearchParams({
        page: page.toString(),
        page_size: usersPageSize.toString(),
        search: search
      });
      const res = await fetch(`${BACKEND_URL}/admin/users?${queryParams.toString()}`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setUsersList(data.data.users || []);
        setUsersTotal(data.data.total || 0);
      }
    } catch (e) {
      console.error("Failed to fetch user directory:", e);
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const fetchConfigs = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/admin/config`, {
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        setConfigs(data.data || {});
        setBlocklist(data.data.keyword_blocklist || '');
      }
    } catch (e) {
      console.error("Failed to fetch platform configurations:", e);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchConfigs();
  }, []);

  useEffect(() => {
    if (activeSubTab === 'queue') {
      fetchTasks(tasksPage);
      const interval = setInterval(() => fetchTasks(tasksPage), 5000);
      return () => clearInterval(interval);
    } else if (activeSubTab === 'users') {
      fetchUsers(usersPage, userSearch);
    }
  }, [activeSubTab, tasksPage, usersPage]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setUsersPage(1);
    fetchUsers(1, userSearch);
  };

  const handleUserEditClick = (user) => {
    setEditingUser(user);
    setEditForm({
      email: user.email || '',
      role: user.role || 'user',
      plan: user.plan || 'free',
      quota_videos_per_day: user.quota_videos_per_day ?? 5,
      quota_videos_per_month: user.quota_videos_per_month ?? 50,
      is_active: user.is_active ?? true
    });
  };

  const handleUserUpdate = async (e) => {
    e.preventDefault();
    if (!editingUser) return;
    setIsUpdatingUser(true);
    addLog(`Updating configurations for user: ${editingUser.user_id}`);
    try {
      const res = await fetch(`${BACKEND_URL}/admin/users/${editingUser.user_id}`, {
        method: 'PATCH',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(editForm)
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`Successfully updated user ${editingUser.user_id}`);
        setEditingUser(null);
        fetchUsers(usersPage, userSearch);
        fetchStats();
      } else {
        alert(`Failed to update user: ${data.message}`);
      }
    } catch (err) {
      alert(`Error updating user details: ${err.message}`);
    } finally {
      setIsUpdatingUser(false);
    }
  };

  const handleSaveBlocklist = async (e) => {
    e.preventDefault();
    setIsSavingConfig(true);
    addLog("Updating platform keyword blocklist configurations...");
    try {
      const res = await fetch(`${BACKEND_URL}/admin/config`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          key: 'keyword_blocklist',
          value: blocklist
        })
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog("Keyword blocklist updated successfully.");
        alert("Platform blocklist configurations saved successfully!");
        fetchConfigs();
      } else {
        alert(`Failed to save configurations: ${data.message}`);
      }
    } catch (err) {
      alert(`Error saving platform configs: ${err.message}`);
    } finally {
      setIsSavingConfig(false);
    }
  };

  const stopTask = async (taskId) => {
    if (!window.confirm(`Stop running compilation pipeline ${taskId}?`)) return;
    try {
      const res = await fetch(`${BACKEND_URL}/tasks/${taskId}/stop`, {
        method: 'POST',
        headers: await getHeaders()
      });
      const data = await res.json();
      if (data.status === 200) {
        addLog(`Stopped task: ${taskId}`);
        fetchTasks(tasksPage);
        fetchStats();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getTaskStateBadge = (state) => {
    switch (state) {
      case 0:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Waiting</span>;
      case 1:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Success</span>;
      case 2:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">Failed</span>;
      case 3:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">Stopped</span>;
      case 4:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" /> Running
          </span>
        );
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">Unknown</span>;
    }
  };

  const getTaskSubject = (task) => {
    if (task.params?.video_subject) return task.params.video_subject;
    if (task.script) {
      const sentence = task.script.split(/[.!?]/)[0].trim();
      return sentence.length > 40 ? sentence.substring(0, 37) + '...' : sentence;
    }
    return 'Short Video Generation';
  };

  return (
    <div className="space-y-8 animate-fade-in relative">
      
      {/* Page Header */}
      <header className="page-header flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="page-title text-2xl md:text-3xl font-extrabold flex items-center gap-2">
            <Lock className="text-yellow-400" size={24} /> Admin Portal
          </h2>
          <p className="page-subtitle text-zinc-400 text-sm md:text-base">System-wide monitoring, user accounts provision, daily limits edit, and keyword moderation controls.</p>
        </div>
        <button 
          onClick={() => { fetchStats(); if (activeSubTab === 'queue') fetchTasks(); else if (activeSubTab === 'users') fetchUsers(); }}
          className="btn btn-secondary text-xs bg-white/5 border border-white/5 hover:bg-white/10 px-4 py-2 rounded-xl flex items-center gap-2 self-start md:self-auto"
        >
          🔄 Force Refresh
        </button>
      </header>

      {/* Stats Cards Section */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {[
          { title: 'Total Registered Users', value: stats.total_users, icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/5', border: 'border-blue-500/10' },
          { title: 'Compiled Videos Count', value: stats.total_tasks, icon: Video, color: 'text-pink-400', bg: 'bg-pink-500/5', border: 'border-pink-500/10' },
          { title: 'Active Processing Queue', value: stats.active_tasks, icon: Activity, color: 'text-amber-400', bg: 'bg-amber-500/5', border: 'border-amber-500/10' },
          { title: 'Cloud CDN Uploads', value: stats.cdn_uploads, icon: Cloud, color: 'text-emerald-400', bg: 'bg-emerald-500/5', border: 'border-emerald-500/10' }
        ].map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div key={idx} className={`glass-panel p-4 md:p-6 flex items-center justify-between border ${stat.border} ${stat.bg}`}>
              <div className="space-y-1 md:space-y-2">
                <span className="text-[10px] md:text-xs font-bold text-zinc-500 uppercase tracking-wider block">{stat.title}</span>
                <span className="text-2xl md:text-3xl font-extrabold text-zinc-100">{isLoadingStats ? '...' : stat.value}</span>
              </div>
              <div className={`p-2.5 md:p-3.5 rounded-xl bg-zinc-900 border border-white/5 ${stat.color}`}>
                <Icon size={20} />
              </div>
            </div>
          );
        })}
      </section>

      {/* Admin Operations Sub-Tabs Navigation */}
      <section className="glass-panel p-1.5 flex gap-2 w-max bg-zinc-900/40 border border-white/5 rounded-xl">
        {[
          { id: 'queue', label: 'Active Queue', icon: Activity },
          { id: 'users', label: 'User Directory', icon: Users },
          { id: 'config', label: 'Platform Config', icon: Settings }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`
                px-4.5 py-2.5 rounded-lg text-xs md:text-sm font-semibold flex items-center gap-2 transition-all
                ${isActive 
                  ? 'bg-yellow-400 text-black shadow-lg shadow-yellow-400/5' 
                  : 'text-zinc-400 hover:text-zinc-100 hover:bg-white/3'}
              `}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </section>

      {/* Active Sub-Tab View Rendering */}
      <section className="space-y-6">
        
        {/* TAB 1: Active Queue Table */}
        {activeSubTab === 'queue' && (
          <div className="glass-panel p-6 overflow-hidden space-y-4">
            <div className="flex justify-between items-center pb-4 border-b border-white/5">
              <h3 className="text-base md:text-lg font-bold text-zinc-100 flex items-center gap-2">
                <Activity size={20} className="text-yellow-400" />
                Active Processing Queue
              </h3>
              <span className="text-xs text-zinc-500">Auto-refresh active (5s)</span>
            </div>

            <div className="overflow-x-auto w-full">
              <table className="min-w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/5 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">
                    <th className="pb-4.5 pl-2">User Email</th>
                    <th className="pb-4.5">Task ID</th>
                    <th className="pb-4.5">Target Theme</th>
                    <th className="pb-4.5 w-1/4">Progress</th>
                    <th className="pb-4.5">Status</th>
                    <th className="pb-4.5 text-right pr-2">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-xs md:text-sm text-zinc-300">
                  {isLoadingTasks && tasks.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-500">
                        <Loader2 className="animate-spin inline-block mr-2" size={16} /> Loading tasks queue...
                      </td>
                    </tr>
                  ) : tasks.filter(t => t.state === 0 || t.state === 4).length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-zinc-500">
                        No active compilation tasks running in pipeline.
                      </td>
                    </tr>
                  ) : (
                    tasks.filter(t => t.state === 0 || t.state === 4).map((task) => (
                      <tr key={task.task_id} className="hover:bg-white/[0.01] transition-all">
                        <td className="py-4 pl-2 font-medium text-zinc-400 max-w-[150px] truncate" title={task.user_email || task.user_id}>
                          {task.user_email || task.user_id}
                        </td>
                        <td className="py-4 font-mono text-[10px] text-zinc-500">{task.task_id.substring(0, 8)}...</td>
                        <td className="py-4 font-semibold text-zinc-200 max-w-[200px] truncate" title={getTaskSubject(task)}>
                          {getTaskSubject(task)}
                        </td>
                        <td className="py-4">
                          <div className="space-y-1.5 pr-4">
                            <div className="flex justify-between text-[10px] font-bold text-zinc-400">
                              <span>{task.progress}%</span>
                              <span className="italic font-normal">{task.status_message || 'In progress'}</span>
                            </div>
                            <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden border border-white/5">
                              <div className="bg-yellow-400 h-full transition-all duration-300 rounded-full" style={{ width: `${task.progress}%` }} />
                            </div>
                          </div>
                        </td>
                        <td className="py-4">{getTaskStateBadge(task.state)}</td>
                        <td className="py-4 text-right pr-2">
                          <button
                            onClick={() => stopTask(task.task_id)}
                            className="p-2 bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white rounded-lg transition-all"
                            title="Abort task execution"
                          >
                            <Pause size={14} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: User Privilege Directory */}
        {activeSubTab === 'users' && (
          <div className="glass-panel p-6 overflow-hidden space-y-6">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 pb-4 border-b border-white/5">
              <h3 className="text-base md:text-lg font-bold text-zinc-100 flex items-center gap-2">
                <Users size={20} className="text-yellow-400" />
                User Privilege Directory
              </h3>

              {/* User search bar */}
              <form onSubmit={handleSearchSubmit} className="flex gap-2 w-full sm:max-w-xs">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" size={14} />
                  <input
                    type="text"
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                    placeholder="Search ID or Email..."
                    className="w-full bg-black/40 border border-white/5 rounded-xl pl-9.5 pr-4 py-2 text-xs md:text-sm text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all"
                  />
                </div>
                <button type="submit" className="btn btn-secondary py-2 text-xs">Search</button>
              </form>
            </div>

            <div className="overflow-x-auto w-full">
              <table className="min-w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/5 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">
                    <th className="pb-4.5 pl-2">User ID</th>
                    <th className="pb-4.5">Email</th>
                    <th className="pb-4.5">Role</th>
                    <th className="pb-4.5">Plan</th>
                    <th className="pb-4.5">Daily Quota</th>
                    <th className="pb-4.5">Status</th>
                    <th className="pb-4.5">Usage Today</th>
                    <th className="pb-4.5">Total Generated</th>
                    <th className="pb-4.5 text-right pr-2">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-xs md:text-sm text-zinc-300">
                  {isLoadingUsers ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-zinc-500">
                        <Loader2 className="animate-spin inline-block mr-2" size={16} /> Loading users directory...
                      </td>
                    </tr>
                  ) : usersList.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-zinc-500">
                        No registered users found.
                      </td>
                    </tr>
                  ) : (
                    usersList.map((userItem) => (
                      <tr key={userItem.user_id} className="hover:bg-white/[0.01] transition-all">
                        <td className="py-4 pl-2 font-mono text-[10px] text-zinc-500 max-w-[120px] truncate" title={userItem.user_id}>
                          {userItem.user_id}
                        </td>
                        <td className="py-4 font-semibold text-zinc-200 max-w-[150px] truncate" title={userItem.email}>
                          {userItem.email || <span className="text-zinc-600 font-normal italic">None</span>}
                        </td>
                        <td className="py-4">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            userItem.role === 'admin' 
                              ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' 
                              : 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20'
                          }`}>
                            {userItem.role}
                          </span>
                        </td>
                        <td className="py-4">
                          <span className="capitalize">{userItem.plan}</span>
                        </td>
                        <td className="py-4 font-semibold text-zinc-200">{userItem.quota_videos_per_day}</td>
                        <td className="py-4">
                          {userItem.is_active ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">Deactivated</span>
                          )}
                        </td>
                        <td className="py-4 text-zinc-400">{userItem.usage_today}</td>
                        <td className="py-4 text-zinc-400">{userItem.total_tasks}</td>
                        <td className="py-4 text-right pr-2">
                          <button
                            onClick={() => handleUserEditClick(userItem)}
                            className="p-2 bg-yellow-400/10 text-yellow-400 hover:bg-yellow-400 hover:text-black rounded-lg transition-all"
                            title="Edit user settings"
                          >
                            <Edit2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Users Pagination */}
            {usersTotal > usersPageSize && (
              <div className="flex justify-between items-center pt-4 border-t border-white/5">
                <span className="text-xs text-zinc-500">
                  Showing {((usersPage - 1) * usersPageSize) + 1} - {Math.min(usersPage * usersPageSize, usersTotal)} of {usersTotal} users
                </span>
                <div className="flex items-center gap-2">
                  <button
                    disabled={usersPage <= 1}
                    onClick={() => setUsersPage(usersPage - 1)}
                    className="p-2 bg-white/5 border border-white/5 hover:bg-white/10 rounded-lg text-zinc-400 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-all"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="text-xs text-zinc-300 font-bold px-2">Page {usersPage}</span>
                  <button
                    disabled={usersPage * usersPageSize >= usersTotal}
                    onClick={() => setUsersPage(usersPage + 1)}
                    className="p-2 bg-white/5 border border-white/5 hover:bg-white/10 rounded-lg text-zinc-400 hover:text-white disabled:opacity-30 disabled:pointer-events-none transition-all"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Configuration Forms */}
        {activeSubTab === 'config' && (
          <div className="glass-panel p-6 overflow-hidden space-y-6">
            <h3 className="text-base md:text-lg font-bold text-zinc-100 flex items-center gap-2 pb-4 border-b border-white/5">
              <Settings size={20} className="text-yellow-400" />
              Platform configurations & spam blocklists
            </h3>

            <form onSubmit={handleSaveBlocklist} className="space-y-5 max-w-2xl">
              <div className="form-group flex flex-col gap-2.5">
                <label className="form-label text-sm font-semibold text-zinc-300">Keyword Blocklist (Comma-separated)</label>
                <textarea
                  value={blocklist}
                  onChange={(e) => setBlocklist(e.target.value)}
                  placeholder="e.g. spam, scam, explicit, dangerous"
                  className="w-full h-32 bg-black/40 border border-white/5 rounded-xl p-4 text-xs md:text-sm text-zinc-100 placeholder-zinc-500 focus:border-yellow-400 outline-none transition-all resize-none font-mono"
                />
                <small className="text-zinc-500 text-xs leading-relaxed">
                  Provide comma-separated keywords to restrict. Any video prompt submitted containing a matching word will be automatically rejected with a <code>400 Bad Request</code> response.
                </small>
              </div>

              <button
                type="submit"
                disabled={isSavingConfig}
                className="btn btn-primary px-6 py-3 rounded-xl font-bold text-sm shadow-lg shadow-yellow-500/10 active:scale-95 transition-all flex items-center gap-2"
              >
                {isSavingConfig ? (
                  <>
                    <Loader2 className="animate-spin" size={16} /> Applying configurations...
                  </>
                ) : (
                  <>
                    <Save size={16} /> Save Configurations
                  </>
                )}
              </button>
            </form>
          </div>
        )}

      </section>

      {/* User Editing Overlay Modal Dialog (Popup panel) */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-6 z-[200] animate-fade-in">
          <div className="glass-panel border border-white/10 rounded-2xl bg-zinc-950/90 w-full max-w-md flex flex-col relative overflow-hidden">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-white/5">
              <h3 className="text-base font-bold text-zinc-100 flex items-center gap-2">
                <ShieldAlert className="text-yellow-400" size={18} /> Modify User Settings
              </h3>
              <button 
                onClick={() => setEditingUser(null)}
                className="p-1.5 rounded-full text-zinc-400 hover:text-white hover:bg-white/5 transition-all flex-shrink-0"
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleUserUpdate} className="p-6 space-y-5">
              <div className="space-y-1">
                <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">User Identifier</span>
                <p className="font-mono text-xs text-zinc-300 break-all">{editingUser.user_id}</p>
              </div>

              <div className="form-group flex flex-col gap-1.5">
                <label className="form-label text-xs text-zinc-300 font-semibold">User Email</label>
                <input
                  type="email"
                  required
                  value={editForm.email}
                  onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                  className="bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-xs md:text-sm text-zinc-100 placeholder-zinc-600 focus:border-yellow-400 outline-none transition-all"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="form-group flex flex-col gap-1.5">
                  <label className="form-label text-xs text-zinc-300 font-semibold">User Role</label>
                  <select
                    value={editForm.role}
                    onChange={(e) => setEditForm({...editForm, role: e.target.value})}
                    className="bg-zinc-900 border border-white/5 rounded-xl px-3 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                <div className="form-group flex flex-col gap-1.5">
                  <label className="form-label text-xs text-zinc-300 font-semibold">Pricing Plan</label>
                  <select
                    value={editForm.plan}
                    onChange={(e) => setEditForm({...editForm, plan: e.target.value})}
                    className="bg-zinc-900 border border-white/5 rounded-xl px-3 py-2.5 text-xs text-zinc-100 focus:border-yellow-400 outline-none transition-all cursor-pointer"
                  >
                    <option value="free">Free</option>
                    <option value="premium">Premium</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="form-group flex flex-col gap-1.5">
                  <label className="form-label text-xs text-zinc-300 font-semibold">Daily Video Quota</label>
                  <input
                    type="number"
                    min="1"
                    value={editForm.quota_videos_per_day}
                    onChange={(e) => setEditForm({...editForm, quota_videos_per_day: parseInt(e.target.value) || 1})}
                    className="bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-xs md:text-sm text-zinc-100 focus:border-yellow-400 outline-none transition-all"
                  />
                </div>

                <div className="form-group flex flex-col gap-1.5">
                  <label className="form-label text-xs text-zinc-300 font-semibold">Monthly Video Quota</label>
                  <input
                    type="number"
                    min="1"
                    value={editForm.quota_videos_per_month}
                    onChange={(e) => setEditForm({...editForm, quota_videos_per_month: parseInt(e.target.value) || 1})}
                    className="bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-xs md:text-sm text-zinc-100 focus:border-yellow-400 outline-none transition-all"
                  />
                </div>
              </div>

              <div className="form-group flex items-center gap-3.5 py-1">
                <input
                  type="checkbox"
                  id="edit_is_active"
                  checked={editForm.is_active}
                  onChange={(e) => setEditForm({...editForm, is_active: e.target.checked})}
                  className="w-4 h-4 rounded bg-zinc-900 border-white/10 text-yellow-400 focus:ring-yellow-400/20 cursor-pointer"
                />
                <label htmlFor="edit_is_active" className="cursor-pointer text-xs md:text-sm text-zinc-400 select-none hover:text-zinc-300">
                  Allow user account access (Active Status)
                </label>
              </div>

              <div className="pt-4 border-t border-white/5 flex justify-end gap-3">
                <button 
                  type="button" 
                  onClick={() => setEditingUser(null)}
                  className="btn btn-secondary text-xs px-4 py-2.5"
                  disabled={isUpdatingUser}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary text-xs px-5 py-2.5 flex items-center gap-1.5"
                  disabled={isUpdatingUser}
                >
                  {isUpdatingUser ? (
                    <>
                      <Loader2 className="animate-spin" size={12} /> Saving...
                    </>
                  ) : (
                    <>
                      <Save size={12} /> Save Updates
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
