import React from 'react';
import { ReactFlow, Background, Controls, Handle, Position, ReactFlowProvider, useReactFlow } from '@xyflow/react';
import { 
  Tv, 
  Video, 
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
  Database,
  Cloud,
  Layers,
  ArrowRight,
  Info,
  Terminal,
  FileText,
  Volume2,
  Type,
  Film,
  Pause,
  Trash2,
  Mail
} from 'lucide-react';
import '@xyflow/react/dist/style.css';

// Custom icons
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

const PipelineNode = ({ data }) => {
  const { label, icon: Icon, status, description } = data;
  
  let borderColor = 'rgba(255, 255, 255, 0.08)';
  let glowColor = 'transparent';
  let textColor = 'text-zinc-400';
  let bg = 'rgba(255, 255, 255, 0.01)';
  let iconColor = 'text-zinc-500';
  let isPulse = false;

  if (status === 'success') {
    borderColor = '#10b981';
    glowColor = 'rgba(16, 185, 129, 0.1)';
    textColor = 'text-emerald-400';
    bg = 'rgba(16, 185, 129, 0.04)';
    iconColor = 'text-emerald-500';
  } else if (status === 'processing') {
    borderColor = '#3b82f6';
    glowColor = 'rgba(59, 130, 246, 0.25)';
    textColor = 'text-blue-400';
    bg = 'rgba(59, 130, 246, 0.05)';
    iconColor = 'text-blue-500';
    isPulse = true;
  } else if (status === 'failed') {
    borderColor = '#ef4444';
    glowColor = 'rgba(239, 68, 68, 0.2)';
    textColor = 'text-red-400';
    bg = 'rgba(239, 68, 68, 0.05)';
    iconColor = 'text-red-500';
  } else if (status === 'stopped') {
    borderColor = '#ffd700';
    glowColor = 'rgba(255, 215, 0, 0.2)';
    textColor = 'text-yellow-500';
    bg = 'rgba(255, 215, 0, 0.05)';
    iconColor = 'text-yellow-500';
  }

  return (
    <div 
      className={`p-4 rounded-2xl flex flex-col gap-1 w-[210px] backdrop-blur-md transition-all duration-300 relative overflow-hidden ${isPulse ? 'animate-pulse-glow' : ''}`}
      style={{
        border: `1.5px solid ${borderColor}`,
        background: bg,
        boxShadow: `0 8px 32px 0 rgba(0, 0, 0, 0.3), 0 0 14px ${glowColor}`,
      }}
    >
      {/* Target handle - hidden on the very first node */}
      {label !== 'Prompt Input' && (
        <Handle 
          type="target" 
          position={Position.Left} 
          style={{ 
            background: borderColor, 
            width: '8px', 
            height: '8px', 
            border: '1.5px solid rgba(255, 255, 255, 0.2)',
            boxShadow: `0 0 8px ${glowColor}`
          }} 
        />
      )}
      <div className="flex items-center gap-3">
        <div className={`bg-white/2 border border-white/5 rounded-lg w-9 h-9 flex items-center justify-center flex-shrink-0 ${iconColor}`}>
          {Icon && <Icon size={18} />}
        </div>
        <div className="flex-1 text-left min-w-0">
          <div className={`font-bold text-sm tracking-wide truncate ${status !== 'pending' ? textColor : 'text-zinc-100'}`}>{label}</div>
          <div className="text-[11px] text-zinc-400 font-medium truncate">{description}</div>
        </div>
      </div>

      {status === 'processing' && (
        <div className="flex items-center gap-1.5 mt-0.5">
          <div className="w-2 h-2 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-[8px] text-blue-500 font-extrabold tracking-wider">PROCESSING...</span>
        </div>
      )}
      {status === 'failed' && <div className="text-[8px] text-red-500 font-extrabold mt-0.5 tracking-wider">ERROR STAGE</div>}
      {status === 'stopped' && <div className="text-[8px] text-yellow-500 font-extrabold mt-0.5 tracking-wider">PAUSED / STOPPED</div>}

      {/* Source handle - hidden on the very last node */}
      {label !== 'Email Report' && (
        <Handle 
          type="source" 
          position={Position.Right} 
          style={{ 
            background: borderColor, 
            width: '8px', 
            height: '8px', 
            border: '1.5px solid rgba(255, 255, 255, 0.2)',
            boxShadow: `0 0 8px ${glowColor}`
          }} 
        />
      )}
    </div>
  );
};

const nodeTypes = {
  pipelineNode: PipelineNode
};

function FlowInner({ nodes, edges, isCompleted }) {
  const { fitView } = useReactFlow();

  React.useEffect(() => {
    // Fit view initially with a small delay to ensure container dimensions are calculated
    const timer = setTimeout(() => {
      fitView({ padding: 0.15, duration: 400 });
    }, 150);
    return () => clearTimeout(timer);
  }, [fitView]);

  // Fit view when nodes change (e.g. status updates)
  React.useEffect(() => {
    const timer = setTimeout(() => {
      fitView({ padding: 0.15, duration: 300 });
    }, 100);
    return () => clearTimeout(timer);
  }, [nodes, fitView]);

  return (
    <ReactFlow 
      nodes={nodes} 
      edges={edges} 
      nodeTypes={nodeTypes}
      minZoom={0.15}
      maxZoom={1.5}
      nodesConnectable={false}
      nodesDraggable={false}
      elementsSelectable={false}
      zoomOnScroll={true}
      zoomOnPinch={true}
      panOnDrag={true}
      fitView
    >
      <Background color="rgba(255,255,255,0.03)" gap={16} size={1} />
    </ReactFlow>
  );
}

export default function Visualizer({ selectedTask, handleStopTask, handleReinitTask, handleDeleteTask, STREAM_URL, getToken }) {
  const [token, setToken] = React.useState('');

  React.useEffect(() => {
    const fetchToken = async () => {
      if (getToken) {
        try {
          const t = await getToken();
          setToken(t || '');
        } catch (e) {
          console.error("Error fetching token for visualizer:", e);
        }
      }
    };
    fetchToken();
  }, [getToken]);

  if (!selectedTask) {
    return (
      <div className="glass-panel p-8 text-center text-zinc-500 flex items-center justify-center h-48">
        No generation tasks registered yet. Launch a generation script inside Video Studio!
      </div>
    );
  }

  const progress = selectedTask.progress || 0;
  const isFailed = selectedTask.state === -1 || selectedTask.state === 2;
  const isProcessing = selectedTask.state === 4;
  const isStopped = selectedTask.state === 3;

  const steps = [
    { id: 'start', label: 'Prompt Input', progress: 5, description: 'Task Triggered', icon: Terminal },
    { id: 'script', label: 'LLM Script', progress: 15, description: 'Script generated via LLM', icon: FileText },
    { id: 'audio', label: 'TTS Audio', progress: 45, description: 'Synthesizing narrator voice', icon: Volume2 },
    { id: 'subtitles', label: 'SRT Subtitles', progress: 60, description: 'Aligning timecodes', icon: Type },
    { id: 'materials', label: 'Pexels Clips', progress: 75, description: 'Downloading visual clips', icon: Film },
    { id: 'ffmpeg', label: 'FFmpeg Render', progress: 90, description: 'Rendering subtitle & BGM overlays', icon: Video },
    { id: 'cloudinary', label: 'Cloud CDN', progress: 95, description: 'Uploading compiled video', icon: Cloud },
    { id: 'youtube', label: 'YouTube Short', progress: 99, description: 'Auto-publishing to channel', icon: Youtube },
    { id: 'email', label: 'Email Report', progress: 100, description: 'Sending run status report', icon: Mail },
  ];

  const getStatus = (idx, step) => {
    const targetProgress = step.progress;
    const prevProgress = idx > 0 ? steps[idx - 1].progress : 0;

    if (isStopped && progress < targetProgress) {
      if (progress >= prevProgress && progress < targetProgress) return 'stopped';
      return 'pending';
    }
    if (isFailed && progress < targetProgress) {
      if (progress >= prevProgress && progress < targetProgress) return 'failed';
      return 'pending';
    }
    if (progress >= targetProgress) return 'success';
    if (isProcessing && progress >= prevProgress && progress < targetProgress) return 'processing';
    return 'pending';
  };

  const nodes = steps.map((step, idx) => {
    const status = getStatus(idx, step);
    const xPos = idx * 260 + 30; // Spaced out horizontally to prevent overlap
    const yPos = 80;            // Centered vertically

    return {
      id: step.id,
      type: 'pipelineNode',
      data: { 
        label: step.label,
        description: step.description,
        icon: step.icon,
        status: status
      },
      position: { x: xPos, y: yPos },
    };
  });

  const edges = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    const sourceStatus = getStatus(i, steps[i]);
    const targetStatus = getStatus(i+1, steps[i+1]);
    
    let edgeColor = 'rgba(255, 255, 255, 0.06)';
    let edgeWidth = 1.5;
    let animated = false;

    if (sourceStatus === 'success') {
      edgeColor = '#10b981';
      edgeWidth = 2.5;
    }
    if (targetStatus === 'processing') {
      edgeColor = '#3b82f6';
      edgeWidth = 2.5;
      animated = true;
    }

    edges.push({
      id: `e-${steps[i].id}-${steps[i+1].id}`,
      source: steps[i].id,
      target: steps[i+1].id,
      animated,
      style: { stroke: edgeColor, strokeWidth: edgeWidth, transition: 'all 0.3s ease' }
    });
  }

  const isCompleted = selectedTask.state === 1;

  // Shorten Task ID for cleaner rendering on small screens
  const displayId = selectedTask.task_id.substring(0, 8) + '...';

  return (
    <div className="glass-panel p-6 mb-8 flex flex-col transition-all duration-300">
      
      {/* Responsive Visualizer Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4 mb-5">
        <div className="flex flex-wrap items-center gap-3">
          <Layers className="text-yellow-400 flex-shrink-0" size={20} />
          <h3 className="text-sm md:text-base font-bold text-zinc-100 truncate max-w-[200px] md:max-w-xs" title={selectedTask.params?.video_subject || selectedTask.task_id}>
            Active Task: {selectedTask.params?.video_subject || displayId}
          </h3>
          <span className="text-[11px] text-zinc-500 hidden md:inline">ID: {selectedTask.task_id}</span>
        </div>

        {/* Task state indicators & action buttons */}
        <div className="flex flex-wrap items-center gap-3 md:gap-4.5 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-zinc-400">Progress: <strong className="text-yellow-400">{progress}%</strong></span>
            <span>Status: {
              selectedTask.state === 1 ? <span className="text-emerald-400 font-bold">COMPLETED</span> :
              (selectedTask.state === -1 || selectedTask.state === 2) ? <span className="text-red-400 font-bold">FAILED</span> :
              selectedTask.state === 3 ? <span className="text-yellow-500 font-bold">STOPPED</span> :
              <span className="text-blue-400 font-bold">PROCESSING...</span>
            }</span>
            {selectedTask.status_message && (
              <span className="text-[10px] text-purple-300 bg-purple-500/10 px-2 py-1 rounded-lg border border-purple-500/20 max-w-[200px] truncate" title={selectedTask.status_message}>
                ℹ️ {selectedTask.status_message}
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2 border-t sm:border-t-0 sm:border-l border-white/10 pt-2 sm:pt-0 sm:pl-3">
            {selectedTask.state !== 1 && selectedTask.state !== 2 && selectedTask.state !== 3 && (
              <button 
                onClick={() => handleStopTask(selectedTask.task_id)}
                className="btn btn-secondary px-3 py-1.5 text-[11px] flex items-center gap-1.5 text-yellow-500 bg-yellow-500/5 border-yellow-500/20 hover:bg-yellow-500/10"
              >
                <Pause size={12} /> Stop
              </button>
            )}
            
            <button 
              onClick={() => handleReinitTask(selectedTask)}
              className="btn btn-secondary px-3 py-1.5 text-[11px] flex items-center gap-1.5 text-blue-400 bg-blue-500/5 border-blue-500/20 hover:bg-blue-500/10"
            >
              <RefreshCw size={12} /> Re-run
            </button>

            <button 
              onClick={() => handleDeleteTask(selectedTask.task_id)}
              className="btn btn-secondary px-3 py-1.5 text-[11px] flex items-center gap-1.5 text-red-400 bg-red-500/5 border-red-500/20 hover:bg-red-500/10"
            >
              <Trash2 size={12} /> Delete
            </button>
          </div>
        </div>
      </div>

      {/* Visual Canvas Split & Video Player Grid */}
      <div className={`flex flex-col lg:flex-row gap-5 ${isCompleted ? 'h-[620px] lg:h-[480px]' : 'h-[360px]'}`}>
        
        {/* ReactFlow Node visualizer */}
        <div className="flex-1 min-h-[220px] h-full rounded-xl bg-black/30 border border-white/3 overflow-hidden relative">
          <ReactFlowProvider>
            <FlowInner 
              nodes={nodes}
              edges={edges}
              isCompleted={isCompleted}
            />
          </ReactFlowProvider>
        </div>
        
        {/* Side-by-side Video preview (Visible when finished) */}
        {isCompleted && (
          <div className="w-full lg:w-[280px] xl:w-[320px] h-[240px] lg:h-full rounded-xl bg-black/40 border border-white/5 p-2 flex items-center justify-center relative overflow-hidden flex-shrink-0">
            <video 
              src={selectedTask.cloudinary_url || (selectedTask.videos && selectedTask.videos[0] && (selectedTask.videos[0].startsWith('http') ? selectedTask.videos[0] : `${STREAM_URL}${selectedTask.videos[0]}${token ? `?token=${token}` : ''}`))} 
              controls 
              className="max-h-full max-w-full rounded-lg object-contain" 
            />
          </div>
        )}
      </div>

    </div>
  );
}
