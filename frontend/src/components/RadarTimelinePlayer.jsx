import { useState, useEffect, useRef } from 'react';
import { Play, Pause, SkipBack, SkipForward, CloudRain, Clock, RefreshCw } from 'lucide-react';
import axios from 'axios';

export default function RadarTimelinePlayer({ isVisible, onFrameChange }) {
  const [frames, setFrames] = useState([]);
  const [host, setHost] = useState('https://tilecache.rainviewer.com');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef(null);

  const fetchRadarData = () => {
    setLoading(true);
    axios.get('https://api.rainviewer.com/public/weather-maps.json')
      .then((res) => {
        if (res.data && res.data.radar) {
          const radarHost = res.data.host || 'https://tilecache.rainviewer.com';
          setHost(radarHost);

          const pastFrames = res.data.radar.past || [];
          const nowcastFrames = res.data.radar.nowcast || [];
          const allFrames = [
            ...pastFrames.map(f => ({ ...f, type: 'past' })),
            ...nowcastFrames.map(f => ({ ...f, type: 'nowcast' }))
          ];

          setFrames(allFrames);
          if (allFrames.length > 0) {
            const latestPastIdx = pastFrames.length > 0 ? pastFrames.length - 1 : 0;
            setCurrentIndex(latestPastIdx);
          }
        }
      })
      .catch((err) => {
        console.error("RainViewer API fetch error:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    if (isVisible) {
      fetchRadarData();
    }
  }, [isVisible]);

  // Update active tile URL whenever currentIndex or frames change
  useEffect(() => {
    if (frames.length > 0 && frames[currentIndex] && onFrameChange) {
      const activeFrame = frames[currentIndex];
      const tileUrl = `${host}${activeFrame.path}/256/{z}/{x}/{y}/2/1_1.png`;
      onFrameChange(tileUrl, activeFrame.time);
    }
  }, [currentIndex, frames, host]);

  // Playback timer
  useEffect(() => {
    if (isPlaying && frames.length > 0) {
      intervalRef.current = setInterval(() => {
        setCurrentIndex(prev => (prev + 1) % frames.length);
      }, 800);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, frames.length]);

  if (!isVisible || frames.length === 0) return null;

  const currentFrame = frames[currentIndex];
  const dateObj = currentFrame ? new Date(currentFrame.time * 1000) : new Date();
  const timeFormatted = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const isNowcast = currentFrame?.type === 'nowcast';

  const handleStepBack = () => {
    setIsPlaying(false);
    setCurrentIndex(prev => (prev === 0 ? frames.length - 1 : prev - 1));
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    setCurrentIndex(prev => (prev + 1) % frames.length);
  };

  return (
    <div className="radar-timeline-player-bar ios-glass">
      <div className="radar-player-left">
        <div className="radar-icon-box">
          <CloudRain size={16} color="#38BDF8" className={isPlaying ? 'pulse-anim' : ''} />
        </div>
        <div>
          <div className="radar-player-title-row">
            <span className="radar-player-title">Live Doppler Radar</span>
            <span className={`radar-frame-type-tag ${isNowcast ? 'nowcast' : 'past'}`}>
              {isNowcast ? '⚡ 30m Nowcast' : 'Observed'}
            </span>
          </div>
          <div className="radar-player-time">
            <Clock size={10} /> {timeFormatted} IST ({currentIndex + 1}/{frames.length})
          </div>
        </div>
      </div>

      {/* Progress Track */}
      <div className="radar-progress-track">
        {frames.map((f, idx) => (
          <div
            key={f.time || idx}
            onClick={() => {
              setIsPlaying(false);
              setCurrentIndex(idx);
            }}
            className={`radar-progress-dot ${idx === currentIndex ? 'active' : ''} ${f.type === 'nowcast' ? 'nowcast-dot' : ''}`}
            title={`${new Date(f.time * 1000).toLocaleTimeString()} (${f.type})`}
          />
        ))}
      </div>

      {/* Playback Controls */}
      <div className="radar-player-actions">
        <button onClick={handleStepBack} className="radar-ctrl-btn" title="Step Back 10m">
          <SkipBack size={13} />
        </button>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`radar-ctrl-btn play-btn ${isPlaying ? 'playing' : ''}`}
          title={isPlaying ? 'Pause Radar Loop' : 'Play Radar Animation'}
        >
          {isPlaying ? <Pause size={14} color="#FFF" /> : <Play size={14} color="#FFF" />}
        </button>
        <button onClick={handleStepForward} className="radar-ctrl-btn" title="Step Forward 10m">
          <SkipForward size={13} />
        </button>
        <button onClick={fetchRadarData} disabled={loading} className="radar-ctrl-btn sync-btn" title="Refresh Live Radar Frames">
          <RefreshCw size={12} className={loading ? 'spinning' : ''} />
        </button>
      </div>
    </div>
  );
}
