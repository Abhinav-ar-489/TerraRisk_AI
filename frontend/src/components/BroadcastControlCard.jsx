import { useState } from 'react';
import { Send, Radio, MessageSquare, Share2, CheckCircle, FileCode } from 'lucide-react';
import api from '../services/api';

export default function BroadcastControlCard({
  riskData,
  riskPercentage,
  gaugeColor,
  user,
  triggerToast
}) {
  const [activePreset, setActivePreset] = useState('auto');
  const [dispatching, setDispatching] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState(null);

  const locationName = riskData?.geo_name || 'Kerala Sector';

  const defaultAutoMsg = riskData?.alert_text || (
    riskPercentage >= 70
      ? `CRITICAL LANDSLIDE ALERT: Elevated risk (${riskPercentage.toFixed(1)}%) detected at ${locationName}. Immediate evacuation to nearest relief shelter advised.`
      : `TERRARISK ADVISORY: Monitoring terrain at ${locationName}. Risk: ${riskPercentage.toFixed(1)}%.`
  );

  const [customMessage, setCustomMessage] = useState('');
  const activeMessage = customMessage || defaultAutoMsg;

  const applyPreset = (presetKey) => {
    setActivePreset(presetKey);
    if (presetKey === 'evac') {
      setCustomMessage(`🚨 URGENT EVACUATION ORDER for ${locationName}. Severe landslide probability (${riskPercentage.toFixed(1)}%). Proceed immediately to nearest designated relief camp.`);
    } else if (presetKey === 'watch') {
      setCustomMessage(`⚠️ TERRAIN WATCH for ${locationName}: Soil saturation elevated. Stay alert for slope cracks, avoid hill travel, and monitor official KSDMA bulletins.`);
    } else if (presetKey === 'allclear') {
      setCustomMessage(`✅ ALL CLEAR: Geological stability confirmed at ${locationName}. Nominal moisture parameters restored.`);
    } else {
      setCustomMessage('');
    }
  };

  const handleSendTwilioSms = async (e) => {
    if (e) e.preventDefault();

    setDispatching(true);
    setDispatchStatus(null);
    triggerToast("Connecting to Twilio cellular SMS gateway...", "info");

    try {
      const res = await api.post('/api/broadcast', {
        phone: user?.phone || undefined,
        alert_text: activeMessage
      });

      if (res.data.success) {
        setDispatchStatus({
          status: 'success',
          sid: res.data.sid,
          message: res.data.message || 'SMS Broadcast Dispatched via Twilio',
          timestamp: new Date().toLocaleTimeString()
        });
        triggerToast("✓ Twilio Emergency Broadcast Dispatched", "success");
      } else {
        triggerToast(res.data.error || "Failed to dispatch SMS", "error");
      }
    } catch {
      triggerToast("Error connecting to dispatch gateway.", "error");
    } finally {
      setDispatching(false);
    }
  };

  const openWhatsAppShare = () => {
    const text = `🚨 *TERRARISK EMERGENCY DISASTER ALERT*\n\n${activeMessage}\n\n📍 *Live GIS Map*: https://maps.google.com/?q=${riskData?.lat || 11.5542},${riskData?.lng || 76.1308}\n\nIssued by Kerala State Disaster Management Cell`;
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
  };

  const openTelegramShare = () => {
    const text = `🚨 TERRARISK EMERGENCY DISASTER BULLETIN\n\n${activeMessage}\n\n📍 Sector: (${riskData?.lat || 11.5542}°N, ${riskData?.lng || 76.1308}°E)\n\nIssued by Kerala State Disaster Management Cell`;
    const url = `https://t.me/share/url?url=https://terrarisk.kerala.gov.in&text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
  };

  return (
    <div className="ios-card ios-glass broadcast-control-card">
      <div className="broadcast-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Radio size={16} color="var(--accent)" />
          <h3 className="broadcast-card-title">Communication Gateways</h3>
        </div>
        <span className="live-gateway-badge">CELLULAR & RELAY READY</span>
      </div>

      {/* Preset Quick-Selector Pills */}
      <div className="broadcast-preset-pills">
        <button
          type="button"
          className={`preset-pill ${activePreset === 'evac' ? 'active evac' : ''}`}
          onClick={() => applyPreset('evac')}
        >
          🚨 Evacuation
        </button>
        <button
          type="button"
          className={`preset-pill ${activePreset === 'watch' ? 'active watch' : ''}`}
          onClick={() => applyPreset('watch')}
        >
          ⚠️ Watch
        </button>
        <button
          type="button"
          className={`preset-pill ${activePreset === 'allclear' ? 'active allclear' : ''}`}
          onClick={() => applyPreset('allclear')}
        >
          ✅ All Clear
        </button>
        <button
          type="button"
          className={`preset-pill ${activePreset === 'auto' ? 'active auto' : ''}`}
          onClick={() => applyPreset('auto')}
        >
          ⚡ AI Auto
        </button>
      </div>

      {/* Alert Preview Box */}
      <div className="broadcast-msg-box" style={{ borderLeftColor: gaugeColor }}>
        <div className="broadcast-msg-header">
          <span style={{ fontSize: '10.5px', fontWeight: '800', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
            Generated Emergency Bulletin
          </span>
          <span style={{ fontSize: '11px', fontWeight: '700', color: gaugeColor }}>
            Risk: {riskPercentage.toFixed(1)}%
          </span>
        </div>
        <textarea
          rows={3}
          className="broadcast-textarea"
          value={activeMessage}
          onChange={(e) => {
            setCustomMessage(e.target.value);
            setActivePreset('custom');
          }}
        />
        <div className="broadcast-char-count">
          <span>{activeMessage.length} characters</span>
          <span>Cellular Carrier Compliant</span>
        </div>
      </div>

      {/* Full-width Twilio Cellular SMS Dispatch Action */}
      <button
        type="button"
        className="btn-twilio-blast-full"
        onClick={handleSendTwilioSms}
        disabled={dispatching}
      >
        <Send size={15} />
        <span>{dispatching ? "Transmitting Cellular Broadcast..." : "Dispatch Twilio SMS Broadcast"}</span>
      </button>

      {/* Dispatch Success Feedback Banner */}
      {dispatchStatus && (
        <div className="dispatch-success-banner">
          <CheckCircle size={14} color="#30D158" />
          <span>
            <strong>{dispatchStatus.message}</strong> (SID: <code>{dispatchStatus.sid}</code> at {dispatchStatus.timestamp})
          </span>
        </div>
      )}

      {/* Section 2: Zero-Cost Multi-Channel Community Dispatch */}
      <div className="multi-channel-quick-bar">
        <button
          type="button"
          className="btn-channel-pill wa"
          onClick={openWhatsAppShare}
          title="Share to WhatsApp Panchayat/Ward Groups"
        >
          <Share2 size={13} />
          <span>WhatsApp Broadcast</span>
        </button>

        <button
          type="button"
          className="btn-channel-pill tg"
          onClick={openTelegramShare}
          title="Broadcast to Telegram Disaster Channel"
        >
          <MessageSquare size={13} />
          <span>Telegram Channel</span>
        </button>

        <a
          href="/api/alerts/cap.json"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-channel-pill cap"
          title="View Standardized CAP v1.2 JSON Alert Feed"
        >
          <FileCode size={13} />
          <span>CAP Feed</span>
        </a>
      </div>
    </div>
  );
}
