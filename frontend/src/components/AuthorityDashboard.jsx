import { useState, useEffect, useCallback } from 'react';
import {
  Shield, AlertTriangle, CheckCircle, X, RefreshCw, Radio,
  ThumbsDown, Filter, FileText, Home, Plus, Edit3,
  Trash2, Package, Sparkles, UserCheck
} from 'lucide-react';
import api from '../services/api';
import BroadcastAlertModal from './BroadcastAlertModal';
import AddCampModal from './AddCampModal';
import CampSuppliesModal from './CampSuppliesModal';

const HAZARD_LABELS = {
  mud_crack: { name: 'Mud Crack / Fissure', emoji: '⚡', color: '#F59E0B' },
  stream_overflow: { name: 'Stream Overflow', emoji: '🌊', color: '#38BDF8' },
  rockfall: { name: 'Rockfall / Debris Roll', emoji: '🪨', color: '#EC4899' },
  blocked_road: { name: 'Blocked Roadway', emoji: '🚧', color: '#F97316' },
  slope_movement: { name: 'Slope Movement / Creep', emoji: '⛰️', color: '#EF4444' },
};

const REJECTION_REASONS = [
  { id: 'Spam / Fabricated', label: 'Spam / Fabricated Report' },
  { id: 'Duplicate / Redundant', label: 'Duplicate / Redundant Cluster' },
  { id: 'Minor / Non-Hazard', label: 'Minor Runoff / Non-Hazard' },
  { id: 'Resolved / Already Cleared', label: 'Resolved / Already Cleared' },
];

export default function AuthorityDashboard({
  isOpen,
  onClose,
  user,
  token,
  onClusterUpdated,
  triggerToast
}) {
  const [activeTab, setActiveTab] = useState('triage'); // 'triage' | 'camps' | 'missions' | 'sitrep'
  const [clusters, setClusters] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [shelters, setShelters] = useState([]);
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'pending' | 'verified'
  const [filterType, setFilterType] = useState('all');
  const [actionLoading, setActionLoading] = useState(false);
  const [downloadingSitRep, setDownloadingSitRep] = useState(false);

  // Sub-Modals
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [broadcastModalOpen, setBroadcastModalOpen] = useState(false);
  const [addCampModalOpen, setAddCampModalOpen] = useState(false);
  const [editingShelter, setEditingShelter] = useState(null);
  const [suppliesModalOpen, setSuppliesModalOpen] = useState(false);
  const [selectedSuppliesShelter, setSelectedSuppliesShelter] = useState(null);
  const [selectedRejectReason, setSelectedRejectReason] = useState(REJECTION_REASONS[0].id);

  // Camp Search / Filter
  const [campSearch, setCampSearch] = useState('');
  const [campDistrictFilter, setCampDistrictFilter] = useState('all');

  const fetchTriageData = useCallback(async () => {
    setLoading(true);
    try {
      const [clustersRes, metricsRes, sheltersRes, missionsRes] = await Promise.all([
        api.get('/api/authority/pending-clusters?status=all'),
        api.get('/api/authority/metrics'),
        api.get('/api/shelters'),
        api.get('/api/authority/missions').catch(() => ({ data: { success: true, missions: [] } }))
      ]);

      if (clustersRes.data.success) {
        setClusters(clustersRes.data.clusters || []);
        if (clustersRes.data.clusters && clustersRes.data.clusters.length > 0) {
          setSelectedCluster(prev => {
            if (!prev) return clustersRes.data.clusters[0];
            const updated = clustersRes.data.clusters.find(c => c.cluster_id === prev.cluster_id);
            return updated || clustersRes.data.clusters[0];
          });
        } else {
          setSelectedCluster(null);
        }
      }

      if (metricsRes.data.success) setMetrics(metricsRes.data.metrics);
      if (sheltersRes.data.success) setShelters(sheltersRes.data.shelters || []);
      if (missionsRes.data.success) setMissions(missionsRes.data.missions || []);
    } catch (err) {
      console.error("Triage data fetch error:", err);
      if (triggerToast) triggerToast("Failed to sync authority triage queue.", "error");
    } finally {
      setLoading(false);
    }
  }, [triggerToast]);

  useEffect(() => {
    let ignore = false;
    if (isOpen) {
      const load = async () => {
        try {
          const [clustersRes, metricsRes, sheltersRes, missionsRes] = await Promise.all([
            api.get('/api/authority/pending-clusters?status=all'),
            api.get('/api/authority/metrics'),
            api.get('/api/shelters'),
            api.get('/api/authority/missions').catch(() => ({ data: { success: true, missions: [] } }))
          ]);

          if (!ignore) {
            if (clustersRes.data.success) {
              setClusters(clustersRes.data.clusters || []);
              if (clustersRes.data.clusters && clustersRes.data.clusters.length > 0) {
                setSelectedCluster(clustersRes.data.clusters[0]);
              } else {
                setSelectedCluster(null);
              }
            }
            if (metricsRes.data.success) setMetrics(metricsRes.data.metrics);
            if (sheltersRes.data.success) setShelters(sheltersRes.data.shelters || []);
            if (missionsRes.data.success) setMissions(missionsRes.data.missions || []);
          }
        } catch {
          console.error("Initial triage load error.");
        }
      };
      load();
    }
    return () => { ignore = true; };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleVerify = async () => {
    if (!selectedCluster) return;
    setActionLoading(true);
    try {
      const res = await api.post('/api/incidents/verify', {
        cluster_id: selectedCluster.cluster_id
      });

      if (res.data.success) {
        triggerToast(`✓ Hazard confirmed and verified by Authority.`, "success");
        if (onClusterUpdated) onClusterUpdated();
        await fetchTriageData();
      } else {
        triggerToast(res.data.error || "Verification failed.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Verification request error.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedCluster) return;
    setActionLoading(true);
    try {
      const res = await api.post('/api/incidents/reject', {
        cluster_id: selectedCluster.cluster_id,
        reason: selectedRejectReason
      });

      if (res.data.success) {
        triggerToast(`Cluster marked as rejected (${selectedRejectReason || 'False Alarm'}).`, "info");
        setRejectModalOpen(false);
        if (onClusterUpdated) onClusterUpdated();
        await fetchTriageData();
      } else {
        triggerToast(res.data.error || "Rejection failed.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Rejection request error.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedCluster) return;
    setActionLoading(true);
    try {
      const res = await api.post('/api/incidents/resolve', {
        cluster_id: selectedCluster.cluster_id,
        notes: "Site cleared and hazard mitigated by field emergency response crew."
      });

      if (res.data.success) {
        triggerToast(`✓ Disaster site marked as CLEARED & RESOLVED. Pin removed from live map.`, "success");
        if (onClusterUpdated) onClusterUpdated();
        await fetchTriageData();
      } else {
        triggerToast(res.data.error || "Resolution update failed.", "error");
      }
    } catch (err) {
      triggerToast(err.response?.data?.error || "Resolution request error.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteCamp = async (shelterId, shelterName) => {
    if (!confirm(`Are you sure you want to delete relief camp '${shelterName}'?`)) return;
    try {
      const res = await api.delete(`/api/shelters/${shelterId}`);
      if (res.data.success) {
        triggerToast(`✓ Relief camp '${shelterName}' deleted.`, "info");
        fetchTriageData();
      }
    } catch {
      triggerToast("Failed to delete shelter.", "error");
    }
  };

  const handleExportSitRep = async () => {
    setDownloadingSitRep(true);
    if (triggerToast) triggerToast("Compiling official KSDMA Situation Report (SitRep)...", "info");

    try {
      const res = await api.get('/api/authority/export-sitrep?format=pdf', {
        responseType: 'blob'
      });

      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, "_");
      link.setAttribute('download', `KSDMA_SitRep_${timestamp}.pdf`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      if (triggerToast) triggerToast("✓ Official SitRep PDF downloaded successfully.", "success");
    } catch {
      if (triggerToast) triggerToast("Failed to compile SitRep document.", "error");
    } finally {
      setDownloadingSitRep(false);
    }
  };

  const safeClusters = Array.isArray(clusters) ? clusters : [];
  const safeShelters = Array.isArray(shelters) ? shelters : [];

  const pendingCount = safeClusters.filter(c => c.status === 'pending').length;
  const verifiedCount = safeClusters.filter(c => c.status === 'verified').length;
  const allCount = safeClusters.length;

  const filteredClusters = safeClusters.filter(c => {
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    const matchesHazard = filterType === 'all' || c.primary_hazard_type === filterType;
    return matchesStatus && matchesHazard;
  });

  const filteredShelters = safeShelters.filter(s => {
    const matchesDistrict = campDistrictFilter === 'all' || s.district?.toLowerCase() === campDistrictFilter.toLowerCase();
    const matchesSearch = !campSearch || s.name.toLowerCase().includes(campSearch.toLowerCase()) || s.district?.toLowerCase().includes(campSearch.toLowerCase());
    return matchesDistrict && matchesSearch;
  });

  return (
    <>
      <div className="auth-modal-backdrop" onClick={onClose} style={{ zIndex: 11000 }}>
        <div className="triage-modal-content ios-glass" onClick={(e) => e.stopPropagation()}>
        {/* Top Header */}
        <div className="triage-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="triage-badge-icon">
              <Shield size={24} color="#FFF" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 className="triage-title">DISASTER AUTHORITY COMMAND SUITE</h2>
                <span className="ksdma-tag">KSDMA • SEOC</span>
              </div>
              <span className="triage-subtitle">
                Logged in: {user?.name || "Authority Officer"} ({user?.role?.replace('_', ' ')})
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button className="triage-refresh-btn" onClick={fetchTriageData} title="Refresh Live Feeds">
              <RefreshCw size={15} className={loading ? "spin-anim" : ""} />
              <span>Refresh</span>
            </button>
            <button className="auth-close-btn" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Metrics Ribbon */}
        {metrics && (
          <div className="triage-metrics-ribbon">
            <div
              className={`metric-pill clickable ${statusFilter === 'pending' && activeTab === 'triage' ? 'active' : ''}`}
              onClick={() => { setStatusFilter('pending'); setActiveTab('triage'); }}
              title="Click to view pending citizen reports"
            >
              <span className="metric-lbl">Pending Triage</span>
              <span className="metric-val" style={{ color: '#FF9F0A' }}>{pendingCount || metrics.pending_clusters_count || 0}</span>
            </div>
            <div
              className={`metric-pill clickable ${statusFilter === 'verified' && activeTab === 'triage' ? 'active' : ''}`}
              onClick={() => { setStatusFilter('verified'); setActiveTab('triage'); }}
              title="Click to view verified active hazards on live map"
            >
              <span className="metric-lbl">Verified Hazards</span>
              <span className="metric-val" style={{ color: '#EF4444' }}>{verifiedCount || metrics.active_verified_hazards || 0}</span>
            </div>
            <div
              className={`metric-pill clickable ${activeTab === 'camps' ? 'active' : ''}`}
              onClick={() => setActiveTab('camps')}
              title="Click to view relief shelters"
            >
              <span className="metric-lbl">Relief Camps</span>
              <span className="metric-val" style={{ color: '#38BDF8' }}>{shelters.length}</span>
            </div>
            <div className="metric-pill">
              <span className="metric-lbl">Active Missing</span>
              <span className="metric-val" style={{ color: '#EC4899' }}>{metrics.active_missing_persons || 0}</span>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="authority-nav-tabs">
          <button
            className={`auth-tab-btn ${activeTab === 'triage' ? 'active' : ''}`}
            onClick={() => setActiveTab('triage')}
          >
            <AlertTriangle size={16} />
            <span>Hazard Triage & Verified ({clusters.length})</span>
          </button>

          <button
            className={`auth-tab-btn ${activeTab === 'camps' ? 'active' : ''}`}
            onClick={() => setActiveTab('camps')}
          >
            <Home size={16} />
            <span>Relief Camps & Supplies ({shelters.length})</span>
          </button>

          <button
            className={`auth-tab-btn ${activeTab === 'sitrep' ? 'active' : ''}`}
            onClick={() => setActiveTab('sitrep')}
          >
            <FileText size={16} />
            <span>Emergency SitRep & Alerts</span>
          </button>
        </div>

        {/* TAB 1: INCIDENT TRIAGE & RECTIFICATION */}
        {activeTab === 'triage' && (
          <div className="triage-split-body">
            {/* Left Queue Panel */}
            <div className="triage-queue-panel">
              {/* Status Segmented Pill Filter */}
              <div className="triage-status-bar">
                <button
                  className={`triage-status-tab ${statusFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setStatusFilter('all')}
                  type="button"
                >
                  <span>All Active</span>
                  <span className="triage-tab-count">{allCount}</span>
                </button>
                <button
                  className={`triage-status-tab tab-pending ${statusFilter === 'pending' ? 'active' : ''}`}
                  onClick={() => setStatusFilter('pending')}
                  type="button"
                >
                  <span>Pending</span>
                  <span className="triage-tab-count">{pendingCount}</span>
                </button>
                <button
                  className={`triage-status-tab tab-verified ${statusFilter === 'verified' ? 'active' : ''}`}
                  onClick={() => setStatusFilter('verified')}
                  type="button"
                >
                  <span>Verified Live</span>
                  <span className="triage-tab-count">{verifiedCount}</span>
                </button>
              </div>

              <div className="triage-queue-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Filter size={14} color="var(--text-tertiary)" />
                  <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                    Filter Hazard Type:
                  </span>
                </div>
                <select
                  className="triage-hazard-filter"
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                >
                  <option value="all">All Hazards ({clusters.length})</option>
                  <option value="mud_crack">Mud Cracks</option>
                  <option value="stream_overflow">Stream Overflow</option>
                  <option value="rockfall">Rockfall</option>
                  <option value="blocked_road">Blocked Road</option>
                  <option value="slope_movement">Slope Movement</option>
                </select>
              </div>

              {filteredClusters.length === 0 ? (
                <div className="triage-empty-state">
                  <CheckCircle size={32} color="#30D158" />
                  <p style={{ margin: '8px 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                    {statusFilter === 'pending'
                      ? "No pending citizen hazard reports in queue."
                      : statusFilter === 'verified'
                      ? "No verified active hazard zones currently logged."
                      : "All citizen hazard reports triaged and resolved."}
                  </p>
                </div>
              ) : (
                <div className="triage-cluster-list">
                  {filteredClusters.map((cluster) => {
                    const isSelected = selectedCluster?.cluster_id === cluster.cluster_id;
                    const hazardInfo = HAZARD_LABELS[cluster.primary_hazard_type] || HAZARD_LABELS.slope_movement;
                    const hasCV = cluster.max_ai_confidence && cluster.max_ai_confidence >= 0.6;
                    const isVerified = cluster.status === 'verified';

                    return (
                      <div
                        key={cluster.cluster_id}
                        className={`triage-cluster-card is-${cluster.status} ${isSelected ? 'selected' : ''}`}
                        onClick={() => setSelectedCluster(cluster)}
                      >
                        <div className="cluster-card-top">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span className="hazard-emoji-badge">{hazardInfo.emoji}</span>
                            <span className="hazard-title-text" style={{ color: hazardInfo.color }}>
                              {hazardInfo.name}
                            </span>
                          </div>
                          <span className={`cluster-status-pill ${cluster.status}`}>
                            {isVerified ? '🛡️ Verified' : '⚠️ Pending'}
                          </span>
                        </div>

                        {/* Computer Vision Badge */}
                        {hasCV && (
                          <div className="cv-badge-strip">
                            <Sparkles size={12} color="#38BDF8" />
                            <span>AI Vision: {Math.round(cluster.max_ai_confidence * 100)}% Verified</span>
                          </div>
                        )}

                        <div className="cluster-meta-row">
                          <span>📍 ({cluster.lat.toFixed(3)}°N, {cluster.lng.toFixed(3)}°E)</span>
                          <span>👥 {cluster.report_count} Reports</span>
                          <span>⚡ Sev {cluster.max_severity}/5</span>
                        </div>

                        <p className="cluster-desc-preview">{cluster.description}</p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Inspection Panel */}
            <div className="triage-detail-panel">
              {selectedCluster ? (
                <div className="cluster-inspection-view">
                  <div className="inspection-header">
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '20px' }}>
                          {HAZARD_LABELS[selectedCluster.primary_hazard_type]?.emoji || '⚠️'}
                        </span>
                        <h3 className="inspection-title">
                          {HAZARD_LABELS[selectedCluster.primary_hazard_type]?.name}
                        </h3>
                        <span className={`cluster-status-pill ${selectedCluster.status}`}>
                          {selectedCluster.status === 'verified' ? '🛡️ Verified on Map' : '⚠️ Pending Triage'}
                        </span>
                      </div>
                      <span className="inspection-cluster-id">Cluster ID: {selectedCluster.cluster_id}</span>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        className="btn-action-broadcast"
                        onClick={() => setBroadcastModalOpen(true)}
                        title="Broadcast Warning"
                      >
                        <Radio size={14} />
                        <span>Broadcast SMS</span>
                      </button>
                    </div>
                  </div>

                  {/* Verified Notice Banner */}
                  {selectedCluster.status === 'verified' && (
                    <div className="verified-banner-strip">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Shield size={16} color="#30D158" />
                        <strong style={{ fontSize: '12.5px', color: '#30D158' }}>
                          VERIFIED HAZARD • BROADCASTING ON LIVE MAP & ROUTING
                        </strong>
                      </div>
                      <p style={{ margin: 0, fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                        This hazard is actively broadcasted to all citizens and avoided by evacuation routing. Once the field disaster response or road clearance crew has cleared and rectified the site, click <strong>Disaster Site Rectified</strong> below to immediately remove this marker from the public map.
                      </p>
                    </div>
                  )}

                  {/* AI Vision Intelligence Strip */}
                  <div className="cv-intelligence-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <Sparkles size={16} color="#38BDF8" />
                      <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Computer Vision Triage Intelligence</strong>
                    </div>
                    <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {selectedCluster.ai_summary || "Visual telemetry verified against terrain fracture patterns."}
                    </p>
                  </div>

                  {/* Geospatial Stats */}
                  <div className="inspection-stat-grid">
                    <div className="inspection-stat-card">
                      <span className="stat-label">Centroid Coordinates</span>
                      <span className="stat-value">{selectedCluster.lat.toFixed(4)}°N, {selectedCluster.lng.toFixed(4)}°E</span>
                    </div>
                    <div className="inspection-stat-card">
                      <span className="stat-label">Aggregated Reports</span>
                      <span className="stat-value">{selectedCluster.report_count} Reports</span>
                    </div>
                    <div className="inspection-stat-card">
                      <span className="stat-label">Maximum Severity</span>
                      <span className="stat-value" style={{ color: '#EF4444' }}>{selectedCluster.max_severity} / 5</span>
                    </div>
                    <div className="inspection-stat-card">
                      <span className="stat-label">Verified Reporters</span>
                      <span className="stat-value" style={{ color: '#30D158' }}>{selectedCluster.verified_reporters_count ?? 0} / {selectedCluster.report_count}</span>
                    </div>
                  </div>

                  {/* Individual Reports */}
                  <div className="inspection-reports-section">
                    <div className="form-section-label" style={{ margin: '10px 0 6px' }}>Citizen Field Submissions</div>
                    <div className="inspection-reports-list">
                      {selectedCluster.reports?.map((rep, idx) => (
                        <div key={rep.id || idx} className="individual-report-card">
                          <div className="individual-report-header">
                            <div>
                              <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{rep.reporter_name || "Citizen"}</strong>
                              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginLeft: '6px' }}>
                                ({rep.reporter_role || "Citizen"} • {rep.reporter_is_verified ? <span style={{ color: '#30D158' }}>✓ Verified</span> : 'Unverified'})
                              </span>
                            </div>
                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Sev {rep.severity}/5</span>
                          </div>
                          <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            {rep.description || "No textual notes provided."}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Verification & Rectification Decision Buttons */}
                  <div className="inspection-decision-strip">
                    {selectedCluster.status === 'verified' ? (
                      <>
                        <button
                          className="btn-triage-reject"
                          onClick={() => setRejectModalOpen(true)}
                          disabled={actionLoading}
                          title="Revoke / Reject hazard"
                        >
                          <ThumbsDown size={16} />
                          <span>Revoke / Reject</span>
                        </button>

                        <button
                          className="btn-triage-resolve"
                          style={{ flex: 2, background: 'linear-gradient(135deg, #0284C7 0%, #0369A1 100%)', color: '#FFF' }}
                          onClick={handleResolve}
                          disabled={actionLoading}
                          title="Disaster site is rectified & cleared - immediately remove pin from map without penalty"
                        >
                          <CheckCircle size={17} />
                          <span>✓ Disaster Site Rectified (Mark Cleared & Remove from Map)</span>
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="btn-triage-reject"
                          onClick={() => setRejectModalOpen(true)}
                          disabled={actionLoading}
                          title="Reject false report or duplicate"
                        >
                          <ThumbsDown size={16} />
                          <span>Reject False Alarm</span>
                        </button>

                        <button
                          className="btn-triage-resolve"
                          onClick={handleResolve}
                          disabled={actionLoading}
                          title="Disaster site is safe and clear - immediately remove pin from map without penalty"
                        >
                          <CheckCircle size={16} />
                          <span>Mark Cleared</span>
                        </button>

                        <button
                          className="btn-triage-verify"
                          onClick={handleVerify}
                          disabled={actionLoading}
                          title="Confirm real hazard and verify cluster"
                        >
                          <Shield size={16} />
                          <span>Confirm & Verify Hazard</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ) : (
                <div className="triage-empty-state">
                  <Shield size={36} color="var(--text-tertiary)" />
                  <p style={{ margin: '8px 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                    Select an incident cluster from the left queue to inspect and manage.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: RELIEF CAMPS & SUPPLIES */}
        {activeTab === 'camps' && (
          <div className="camps-management-tab">
            <div className="camps-top-bar">
              <div style={{ display: 'flex', gap: '8px', flex: 1 }}>
                <input
                  type="text"
                  className="auth-input"
                  placeholder="Search relief camps..."
                  value={campSearch}
                  onChange={(e) => setCampSearch(e.target.value)}
                  style={{ maxWidth: '280px' }}
                />
                <select
                  className="auth-input"
                  value={campDistrictFilter}
                  onChange={(e) => setCampDistrictFilter(e.target.value)}
                  style={{ maxWidth: '160px' }}
                >
                  <option value="all">All Districts</option>
                  <option value="Wayanad">Wayanad</option>
                  <option value="Idukki">Idukki</option>
                  <option value="Malappuram">Malappuram</option>
                  <option value="Kozhikode">Kozhikode</option>
                  <option value="Palakkad">Palakkad</option>
                </select>
              </div>

              <button
                className="auth-submit-btn"
                onClick={() => { setEditingShelter(null); setAddCampModalOpen(true); }}
                style={{ width: 'auto', padding: '8px 18px' }}
              >
                <Plus size={16} />
                <span>Add Relief Camp</span>
              </button>
            </div>

            <div className="camps-admin-grid">
              {filteredShelters.map(shelter => {
                const available = Math.max(0, shelter.capacity - shelter.occupied);
                const occRate = shelter.occupancy_rate_pct ?? (shelter.capacity > 0 ? Math.round(shelter.occupied / shelter.capacity * 100) : 0);
                const supplies = shelter.supplies || {};

                return (
                  <div key={shelter.id} className="camp-admin-card">
                    <div className="camp-card-top">
                      <div>
                        <h4 className="camp-admin-title">{shelter.name}</h4>
                        <span className="camp-admin-sub">{shelter.district} District • Helpline: {shelter.contact_number}</span>
                      </div>
                      <span className={`camp-status-badge ${shelter.status}`}>
                        {shelter.status?.toUpperCase()}
                      </span>
                    </div>

                    {/* Capacity Progress Bar */}
                    <div className="camp-capacity-bar-wrapper">
                      <div className="capacity-labels">
                        <span>Occupancy: {shelter.occupied} / {shelter.capacity} Beds</span>
                        <span style={{ fontWeight: '700' }}>{available} Available</span>
                      </div>
                      <div className="capacity-bar-bg">
                        <div className="capacity-bar-fill" style={{ width: `${Math.min(100, occRate)}%`, background: occRate >= 90 ? '#EF4444' : '#38BDF8' }} />
                      </div>
                    </div>

                    {/* Supplies Quick Badges */}
                    <div className="camp-supplies-quick-strip">
                      <span title="Drinking Water">💧 {supplies.water_litres ?? 2000}L</span>
                      <span title="Food Packs">🍞 {supplies.food_packets ?? 500} packs</span>
                      <span title="Medical Kits">🩹 {supplies.medical_kits ?? 30} kits</span>
                      <span title="Generator Fuel">⛽ {supplies.fuel_litres ?? 150}L</span>
                    </div>

                    {/* Actions */}
                    <div className="camp-card-actions">
                      <button
                        className="btn-camp-action"
                        onClick={() => { setSelectedSuppliesShelter(shelter); setSuppliesModalOpen(true); }}
                      >
                        <Package size={14} />
                        <span>Supplies</span>
                      </button>

                      <button
                        className="btn-camp-action"
                        onClick={() => { setEditingShelter(shelter); setAddCampModalOpen(true); }}
                      >
                        <Edit3 size={14} />
                        <span>Edit</span>
                      </button>

                      <button
                        className="btn-camp-action delete"
                        onClick={() => handleDeleteCamp(shelter.id, shelter.name)}
                      >
                        <Trash2 size={14} />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}


        {/* TAB 4: SITREP & BROADCAST */}
        {activeTab === 'sitrep' && (
          <div className="sitrep-tab-body">
            <div className="sitrep-promo-card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <FileText size={32} color="#38BDF8" />
                <div>
                  <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)' }}>
                    Official Government of Kerala (KSDMA) Situation Report
                  </h3>
                  <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                    Export formatted, executive Situation Report (SitRep) operational PDF for District Collectors and State Disaster Cells.
                  </p>
                </div>
              </div>

              <button
                className="auth-submit-btn"
                onClick={handleExportSitRep}
                disabled={downloadingSitRep}
                style={{ width: 'auto', padding: '10px 24px', marginTop: '14px' }}
              >
                <FileText size={16} />
                <span>{downloadingSitRep ? "Compiling SitRep PDF..." : "Export Official SitRep PDF"}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>

    {/* Sub-Modals */}
    {rejectModalOpen && (
      <div className="auth-modal-backdrop" style={{ zIndex: 13000 }}>
        <div className="reject-modal-box ios-glass">
          <h3 style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)' }}>
            Reject Incident Cluster
          </h3>
          <p style={{ margin: '0 0 12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            Rejecting this incident cluster will mark the reports as false alarm or duplicate.
          </p>

          <select
            className="auth-input"
            value={selectedRejectReason}
            onChange={(e) => setSelectedRejectReason(e.target.value)}
            style={{ marginBottom: '14px' }}
          >
            {REJECTION_REASONS.map(r => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>

          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button className="btn-secondary" onClick={() => setRejectModalOpen(false)}>Cancel</button>
            <button className="btn-triage-reject" onClick={handleReject} disabled={actionLoading}>
              Confirm Rejection
            </button>
          </div>
        </div>
      </div>
    )}

    {broadcastModalOpen && selectedCluster && (
      <BroadcastAlertModal
        isOpen={broadcastModalOpen}
        onClose={() => setBroadcastModalOpen(false)}
        cluster={selectedCluster}
        user={user}
        token={token || localStorage.getItem('terrarisk_token') || ''}
        triggerToast={triggerToast}
      />
    )}

    {addCampModalOpen && (
      <AddCampModal
        isOpen={addCampModalOpen}
        onClose={() => setAddCampModalOpen(false)}
        token={token || localStorage.getItem('terrarisk_token') || ''}
        editingShelter={editingShelter}
        onCampSaved={() => fetchTriageData()}
        triggerToast={triggerToast}
      />
    )}

    {suppliesModalOpen && selectedSuppliesShelter && (
      <CampSuppliesModal
        isOpen={suppliesModalOpen}
        onClose={() => setSuppliesModalOpen(false)}
        shelter={selectedSuppliesShelter}
        token={token || localStorage.getItem('terrarisk_token') || ''}
        onSuppliesUpdated={() => fetchTriageData()}
        triggerToast={triggerToast}
      />
    )}
  </>
  );
}
