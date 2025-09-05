import React, { useEffect, useState } from "react";
import axios from "axios";

function ChannelSelector({ selectedChannel, setSelectedChannel }) {
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/channels/", {
        withCredentials: true,
      });
      setChannels(res.data || []);
    } catch (err) {
      console.error("Error fetching channels:", err);
    }
  };

  const handleAddChannel = async () => {
    try {
      setLoading(true);
      const res = await axios.post(
        "http://localhost:8000/api/channels/oauth/start",
        {},
        { withCredentials: true }
      );
      if (res.data?.url) {
        window.location.href = res.data.url; // redirect to Google OAuth
      }
    } catch (err) {
      console.error("Error starting OAuth:", err);
      setLoading(false);
    }
  };

  return (
    <div className="mb-4">
      <label className="block font-semibold mb-2">Select Channel:</label>
      <select
        value={selectedChannel || ""}
        onChange={(e) => setSelectedChannel(e.target.value)}
        className="border p-2 rounded w-full"
      >
        <option value="" disabled>
          -- Select a channel --
        </option>
        {channels.map((ch) => (
          <option key={ch.youtube_channel_id} value={ch.youtube_channel_id}>
            {ch.youtube_channel_name}
          </option>
        ))}
      </select>

      <button
        onClick={handleAddChannel}
        disabled={loading}
        className="mt-2 px-4 py-2 bg-blue-600 text-white rounded"
      >
        {loading ? "Redirecting..." : "Add Channel"}
      </button>
    </div>
  );
}

export default ChannelSelector;
