import React, { createContext, useContext, useEffect, useState } from "react";
import apiService from "../features/yt-agent/services/apiService";
import { supabase } from "../supabaseClient";

const SelectedChannelContext = createContext({
  channels: [],
  selectedChannelId: null,
  setSelectedChannelId: (id) => { },
  refreshChannels: async () => { },
  loading: false,
});

export function SelectedChannelProvider({ children }) {
  const [channels, setChannels] = useState([]);
  const [selectedChannelId, setSelectedChannelIdState] = useState(null);
  const [loading, setLoading] = useState(false);

  const LOCAL_KEY = "selectedChannelId";

  // Helper to fetch stats for all channels
  const enrichChannelsWithStats = async (list) => {
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
  };

  // Initial load
  useEffect(() => {
    const init = async () => {
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

        // Set basic list immediately for UI responsiveness
        setChannels(list);

        // Pre-select logic
        const localSaved = localStorage.getItem(LOCAL_KEY);
        if (localSaved) {
          const found = list.find((c) => c.channel_id === localSaved || c.id === localSaved);
          if (found) {
            setSelectedChannelIdState(found.channel_id || found.id);
          } else if (list.length > 0) {
            const firstId = list[0].channel_id || list[0].id;
            setSelectedChannelIdState(firstId);
            localStorage.setItem(LOCAL_KEY, firstId);
          }
        } else if (list.length > 0) {
          const firstId = list[0].channel_id || list[0].id;
          setSelectedChannelIdState(firstId);
          localStorage.setItem(LOCAL_KEY, firstId);
        }

        // Now enrich with stats in the background
        const enriched = await enrichChannelsWithStats(list);
        setChannels(enriched);
      } catch (err) {
        console.error("[SelectedChannelContext] Init failed", err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const refreshChannels = async () => {
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        setChannels([]);
        setSelectedChannelId(null);
        return;
      }

      const res = await apiService.listChannels();
      const list = Array.isArray(res) ? res : (res?.items || []);

      // Update with basic list first
      setChannels(list);

      // Verify current selection still exists
      if (selectedChannelId) {
        const found = list.find((c) => c.channel_id === selectedChannelId || c.id === selectedChannelId);
        if (!found && list.length > 0) {
          const firstId = list[0].channel_id || list[0].id;
          setSelectedChannelId(firstId);
        } else if (!found) {
          setSelectedChannelId(null);
        }
      } else if (list.length > 0) {
        setSelectedChannelId(list[0].channel_id || list[0].id);
      }

      // Enrich with stats
      const enriched = await enrichChannelsWithStats(list);
      setChannels(enriched);
    } catch (err) {
      console.error("[SelectedChannelContext] Refresh failed", err);
    } finally {
      setLoading(false);
    }
  };

  const setSelectedChannelId = (channelId) => {
    setSelectedChannelIdState(channelId);
    if (channelId) {
      localStorage.setItem(LOCAL_KEY, channelId);
    } else {
      localStorage.removeItem(LOCAL_KEY);
    }
  };

  return (
    <SelectedChannelContext.Provider
      value={{
        channels,
        selectedChannelId,
        setSelectedChannelId,
        refreshChannels,
        loading,
      }}
    >
      {children}
    </SelectedChannelContext.Provider>
  );
}

export const useSelectedChannel = () => useContext(SelectedChannelContext);
