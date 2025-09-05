import React, { createContext, useContext, useEffect, useState } from "react";
import api, { getCurrentUser } from "../api/auth";

const SelectedChannelContext = createContext({
  channels: [],
  selectedChannelId: null,
  setSelectedChannelId: async (id) => {},
  refreshChannels: async () => {},
  loading: false,
});

export function SelectedChannelProvider({ children }) {
  const [channels, setChannels] = useState([]);
  const [selectedChannelId, setSelectedChannelIdState] = useState(null);
  const [loading, setLoading] = useState(false);

  const LOCAL_KEY = "selectedChannelId";

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [channelsResp, meResp] = await Promise.allSettled([
          api.get("/api/channels"),
          getCurrentUser(),
        ]);

        let channelsList = [];
        if (channelsResp.status === "fulfilled") {
          channelsList = channelsResp.value.data?.channels || [];
        }
        setChannels(channelsList);

        let serverDefault = null;
        if (meResp.status === "fulfilled") {
          const meData = meResp.value;
          serverDefault = meData?.user?.default_channel_id ?? null;
        }

        const localSaved = localStorage.getItem(LOCAL_KEY);

        if (localSaved) {
          const found = channelsList.find((c) => c.id === localSaved);
          if (found) {
            setSelectedChannelIdState(localSaved);
          } else if (serverDefault) {
            setSelectedChannelIdState(serverDefault);
            localStorage.setItem(LOCAL_KEY, serverDefault);
          } else {
            setSelectedChannelIdState(null);
            localStorage.removeItem(LOCAL_KEY);
          }
        } else if (serverDefault) {
          setSelectedChannelIdState(serverDefault);
          localStorage.setItem(LOCAL_KEY, serverDefault);
        } else {
          setSelectedChannelIdState(null);
        }
      } catch (err) {
        console.error("[SelectedChannelContext] init failed", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const refreshChannels = async () => {
    setLoading(true);
    try {
      const resp = await api.get("/api/channels");
      const list = resp.data?.channels || [];
      setChannels(list);

      const currentSelected = localStorage.getItem(LOCAL_KEY);
      const found = list.find((c) => c.id === currentSelected);
      if (!found) {
        const me = await getCurrentUser();
        const serverDefault = me?.user?.default_channel_id ?? null;
        if (serverDefault) {
          setSelectedChannelIdState(serverDefault);
          localStorage.setItem(LOCAL_KEY, serverDefault);
        } else {
          setSelectedChannelIdState(null);
          localStorage.removeItem(LOCAL_KEY);
        }
      }
    } catch (err) {
      console.error("[SelectedChannelContext] refreshChannels failed", err);
    } finally {
      setLoading(false);
    }
  };

  const setSelectedChannelId = async (channelId) => {
    setSelectedChannelIdState(channelId);
    if (channelId) {
      localStorage.setItem(LOCAL_KEY, channelId);
    } else {
      localStorage.removeItem(LOCAL_KEY);
    }

    try {
      await api.post(`/api/channels/${channelId}/select`);
    } catch (err) {
      console.error("[SelectedChannelContext] Failed to persist selected channel", err);
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
