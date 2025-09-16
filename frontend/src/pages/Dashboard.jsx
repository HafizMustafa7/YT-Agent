import { useState, useEffect } from "react";
import {
  PlayCircle,
  BarChart3,
  ChevronDown,
  PlusCircle,
  Shield,
  Bot,
  Zap,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../supabaseClient";

export default function Dashboard() {
  const [selectedChannel, setSelectedChannel] = useState("Select Channel");
  const [channels, setChannels] = useState([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [driveStatus, setDriveStatus] = useState({ drive_connected: false, token_valid: false, drive_email: null });
  const navigate = useNavigate();

  // ✅ Fetch channels from backend
  useEffect(() => {
    const fetchChannels = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session || !session.user) {
        navigate("/");
        return;
      }

      try {
        const res = await fetch("http://localhost:8000/api/channels/", {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });
        if (!res.ok) throw new Error("Failed to fetch channels");
        const data = await res.json();
        setChannels(data || []);
      } catch (err) {
        console.error("Error fetching channels:", err);
      }
    };

    fetchChannels();
  }, [navigate]);

  // ✅ Fetch Drive connection status
  useEffect(() => {
    const fetchDriveStatus = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session || !session.user) {
        return;
      }

      try {
        const res = await fetch("http://localhost:8000/api/drive/status", {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });
        if (!res.ok) throw new Error("Failed to fetch drive status");
        const data = await res.json();
        setDriveStatus(data);
      } catch (err) {
        console.error("Error fetching drive status:", err);
      }
    };

    fetchDriveStatus();
  }, []);

  const handleLogout = async () => {
    try {
      console.log("[DEBUG] Starting logout process");
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error("[ERROR] Supabase signOut error:", error);
      } else {
        console.log("[DEBUG] Supabase signOut successful");
      }
      localStorage.clear();
      console.log("[DEBUG] localStorage cleared");
      navigate("/");
      console.log("[DEBUG] Navigation to / completed");
    } catch (error) {
      console.error("[ERROR] Logout failed:", error);
      navigate("/");
    }
  };

  // ✅ Start OAuth flow
  const handleAddChannel = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      navigate("/");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/api/channels/oauth", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to start OAuth");
      const data = await res.json();
      window.location.href = data.url; // Redirect to Google OAuth
    } catch (err) {
      console.error("Error starting OAuth:", err);
    }
  };

  // ✅ Disconnect Drive
  const handleDisconnectDrive = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      navigate("/");
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/api/drive/disconnect", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to disconnect Drive");
      // Refresh drive status
      const statusRes = await fetch("http://localhost:8000/api/drive/status", {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (statusRes.ok) {
        const data = await statusRes.json();
        setDriveStatus(data);
      }
    } catch (err) {
      console.error("Error disconnecting Drive:", err);
    }
  };

  return (
    <div className="relative flex flex-col min-h-screen overflow-hidden bg-app">
      {/* 🔹 Top Header */}
      <header className="w-full py-4 shadow-md bg-gradient-to-r from-blue-600 to-cyan-500">
        <div className="flex flex-col items-center justify-center text-center">
          <h1 className="text-2xl font-bold text-white md:text-3xl drop-shadow-lg">
            Automation
          </h1>
          <p className="mt-1 text-sm italic text-white/90">
            Smarter growth. AI-powered efficiency 🚀
          </p>
        </div>
      </header>

      {/* 🔹 Channel selector bar */}
      <div className="flex justify-between p-6">
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="px-4 py-2 btn-glass rounded-xl"
          >
            {selectedChannel}
            <ChevronDown className="w-4 h-4" />
          </button>

          {dropdownOpen && (
            <div className="absolute left-0 top-full z-50 w-80 max-h-60 overflow-y-auto p-3 mt-2 border shadow-2xl bg-black/90 backdrop-blur-xl border-white/30 rounded-2xl">
              {channels.length > 0 ? (
                channels.map((ch) => (
                  <div
                    key={ch.youtube_channel_id}
                    onClick={() => {
                      setSelectedChannel(ch.youtube_channel_name);
                      setDropdownOpen(false);
                    }}
                    className="px-4 py-3 text-sm text-white rounded-xl cursor-pointer hover:bg-white/10 transition-colors duration-200 flex items-center gap-3"
                  >
                    <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-pink-500 rounded-full flex items-center justify-center text-white font-bold text-xs">
                      {ch.youtube_channel_name.charAt(0).toUpperCase()}
                    </div>
                    <span className="truncate">{ch.youtube_channel_name}</span>
                  </div>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-gray-400 text-center">
                  No channels linked yet
                </div>
              )}

              {/* Add new channel (OAuth) */}
              <div className="pt-3 mt-3 border-t border-white/20">
                <div
                  onClick={() => {
                    handleAddChannel();
                    setDropdownOpen(false);
                  }}
                  className="flex items-center gap-3 px-4 py-3 text-sm text-blue-400 rounded-xl cursor-pointer hover:bg-blue-500/20 transition-colors duration-200"
                >
                  <PlusCircle className="w-5 h-5" />
                  <span>Link new YouTube channel</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <button
          onClick={handleLogout}
          className="px-4 py-2 ml-4 text-sm font-medium text-white bg-red-500 rounded-lg hover:bg-red-600"
        >
          Logout
        </button>
      </div>

      {/* 🔹 Main content */}
      <main className="flex flex-col items-center justify-center flex-1 px-6 text-center">
        <h1 className="mb-10 heading-xl">Dashboard</h1>

        <div className="flex flex-col gap-6 md:flex-row">
          <button className="flex items-center justify-center gap-3 btn-primary">
            <PlayCircle className="w-6 h-6" />
            Generate Video
          </button>

          <button className="flex items-center justify-center gap-3 btn-primary bg-teal-600/80 hover:bg-teal-700">
            <BarChart3 className="w-6 h-6" />
            Show Analytics
          </button>
        </div>

        {/* Drive connection status */}
        <div className="mt-10 p-4 border rounded-lg bg-white/10 text-white max-w-md w-full">
          <h2 className="mb-4 text-lg font-semibold">Google Drive Connection</h2>
          {driveStatus.drive_connected ? (
            <>
              <p>Connected as: {driveStatus.drive_email}</p>
              {driveStatus.token_valid ? (
                <p className="text-green-400">Access token is valid</p>
              ) : (
                <p className="text-yellow-400">Access token expired, refreshing...</p>
              )}
              <button
                onClick={handleDisconnectDrive}
                className="mt-4 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
              >
                Disconnect Drive
              </button>
            </>
          ) : (
            <>
              <p className="text-red-400">Not connected to Google Drive</p>
              <button
                onClick={() => navigate("/connect-drive")}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Connect Drive
              </button>
            </>
          )}
        </div>
      </main>

      {/* 🔹 Footer */}
      <footer className="px-10 py-4 text-white border-t bg-gradient-to-r from-blue-600 to-cyan-500 border-white/20">
        <div className="flex items-center justify-between w-full max-w-5xl mx-auto text-sm">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-white" />
            <span className="text-white">AI Powered</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-white" />
            <span className="text-white">Secure</span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-white" />
            <span className="text-white">Fast Performance</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
