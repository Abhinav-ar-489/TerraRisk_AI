// ==============================================================================
// TerraRisk AI - Frontend Supabase Client & Realtime Telemetry Gateway
// ==============================================================================
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

/**
 * Singleton Supabase client instance.
 * Returns null if credentials are not configured (graceful fallback).
 */
export const supabase = (supabaseUrl && supabaseAnonKey)
  ? createClient(supabaseUrl, supabaseAnonKey, {
      realtime: {
        params: {
          eventsPerSecond: 10,
        },
      },
    })
  : null;

/**
 * Check if Supabase cloud integration is actively configured in the frontend.
 */
export const isSupabaseConfigured = () => Boolean(supabase);

/**
 * Subscribe to realtime Emergency Broadcast insertions from Supabase PostgreSQL.
 * @param {Function} onNewAlert - Callback function receiving the new broadcast payload
 * @returns {Object|null} Subscription channel or null if not configured
 */
export const subscribeToEmergencyBroadcasts = (onNewAlert) => {
  if (!supabase) {
    return null;
  }

  const channel = supabase
    .channel('realtime:emergency_broadcasts')
    .on(
      'postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'emergency_broadcasts' },
      (payload) => {
        if (payload?.new && typeof onNewAlert === 'function') {
          onNewAlert(payload.new);
        }
      }
    )
    .subscribe();

  return channel;
};

/**
 * Subscribe to realtime Incident Report insertions and updates.
 * @param {Function} onIncidentChange - Callback function receiving the modified report
 * @returns {Object|null} Subscription channel or null if not configured
 */
export const subscribeToIncidentReports = (onIncidentChange) => {
  if (!supabase) {
    return null;
  }

  const channel = supabase
    .channel('realtime:incident_reports')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'incident_reports' },
      (payload) => {
        if (typeof onIncidentChange === 'function') {
          onIncidentChange(payload);
        }
      }
    )
    .subscribe();

  return channel;
};

export default supabase;
