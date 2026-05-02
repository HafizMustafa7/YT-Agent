/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import apiService from "../features/yt-agent/services/apiService";
import { supabase } from "../supabaseClient";

const SelectedChannelContext = createContext({
  channels: [],
  selectedChannelId: null,
  setSelectedChannelId: () => { },
  refreshChannels: async () => { },
  credits: null,
  refreshCredits: async () => { },
  loading: false,
});

export function SelectedChannelProvider({ children }) {
  const [channels, setChannels] = useState([]);
  const [selectedChannelId, setSelectedChannelIdState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [credits, setCredits] = useState(null);

  const LOCAL_KEY = "selectedChannelId";

  // Helper to fetch stats for all channels
  const enrichChannelsWithStats = useCallback(async (list) => {
    try {
      const enriched = await Promise.all(
        list.map(async (channel) => {
          try {
            const stats = await apiService.getChannelStats(channel.channel_id || channel.id);
            return {
              ...channel,
              subscriber_count: stats.subscriber_count,
              video_count: stats.video_count
            };
          } catch (err) {
            console.error(`Failed to fetch stats for ${channel.channel_id || channel.id}`, err);
            return channel;
          }
        })
      );
      return enriched;
    } catch (err) {
      console.error("[SelectedChannelContext] enrichment failed", err);
      return list;
    }
  }, []);

  // Standalone credits fetch — can be called by any consumer after credit-consuming actions
  const refreshCredits = useCallback(async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;
      const data = await apiService.getUserCredits();
      setCredits(data.credits ?? data ?? null);
    } catch (err) {
      console.error("[SelectedChannelContext] Credits fetch failed:", err);
    }
  }, []);

  // Initial load is now handled entirely by the onAuthStateChange listener

  const refreshChannels = useCallback(async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        setChannels([]);
        setSelectedChannelIdState(null);
        return;
      }

      const res = await apiService.listChannels();
      const list = Array.isArray(res) ? res : (res?.items || []);

      // Update with basic list first
      setChannels(list);

      // Verify current selection still exists
      setSelectedChannelIdState(prev => {
        let newSelection = prev;
        if (prev) {
          const found = list.find((c) => c.channel_id === prev || c.id === prev);
          if (!found && list.length > 0) {
            newSelection = list[0].channel_id || list[0].id;
          } else if (!found) {
            newSelection = null;
          }
        } else if (list.length > 0) {
          newSelection = list[0].channel_id || list[0].id;
        }
        if (newSelection) localStorage.setItem(LOCAL_KEY, newSelection);
        else localStorage.removeItem(LOCAL_KEY);
        return newSelection;
      });

      // Enrich with stats
      const enriched = await enrichChannelsWithStats(list);
      setChannels(enriched);
    } catch (err) {
      console.error("[SelectedChannelContext] Refresh failed", err);
    } finally {
      setLoading(false);
    }
  }, [enrichChannelsWithStats]);

  const setSelectedChannelId = useCallback((channelId) => {
    setSelectedChannelIdState(channelId);
    if (channelId) {
      localStorage.setItem(LOCAL_KEY, channelId);
    } else {
      localStorage.removeItem(LOCAL_KEY);
    }
  }, []);

  // --- Auth State Listener ---
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        // Only fetch on explicit login or initial app load.
        // Ignore TOKEN_REFRESHED and USER_UPDATED to prevent background spam.
        const triggers = ['INITIAL_SESSION', 'SIGNED_IN'];
        if (triggers.includes(event) && session?.access_token) {
          refreshChannels();
          refreshCredits();
        } else if (event === 'SIGNED_OUT') {
          setChannels([]);
          setCredits(null);
          setSelectedChannelIdState(null);
          localStorage.removeItem(LOCAL_KEY);
        }
      }
    );
    return () => subscription.unsubscribe();
  }, [refreshChannels, refreshCredits]);

  // --- Background Periodic Refresh ---
  useEffect(() => {
    const interval = setInterval(() => {
      // Check if we are logged in before refreshing
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session?.access_token) {
          refreshChannels();
          refreshCredits();
        }
      });
    }, 2 * 60 * 1000); // Every 2 minutes
    return () => clearInterval(interval);
  }, [refreshChannels, refreshCredits]);

  // --- Credits Consumption Listener ---
  useEffect(() => {
    const handleCreditsConsumed = () => refreshCredits();
    window.addEventListener('creditsConsumed', handleCreditsConsumed);
    return () => window.removeEventListener('creditsConsumed', handleCreditsConsumed);
  }, [refreshCredits]);
  return (
    <SelectedChannelContext.Provider
      value={{
        channels,
        selectedChannelId,
        setSelectedChannelId,
        refreshChannels,
        credits,
        refreshCredits,
        loading,
      }}
    >
      {children}
    </SelectedChannelContext.Provider>
  );
}

export const useSelectedChannel = () => useContext(SelectedChannelContext);
