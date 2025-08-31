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
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const navigate = useNavigate();

  const channels = ["Channel 1", "Channel 2", "Channel 3"];

  useEffect(() => {
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session || !session.user) {
        navigate("/");
      }
    };
    checkSession();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      navigate("/");
    } catch (error) {
      console.error("Error signing out:", error);
      // Still navigate to home page even if signout fails
      navigate("/");
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
        {/* Channel Selector */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="px-4 py-2 btn-glass rounded-xl"
          >
            {selectedChannel}
            <ChevronDown className="w-4 h-4" />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 z-50 w-48 p-2 mt-2 border shadow-lg bg-black/70 backdrop-blur-xl border-white/20 rounded-xl">
              {channels.map((ch) => (
                <div
                  key={ch}
                  onClick={() => {
                    setSelectedChannel(ch);
                    setDropdownOpen(false);
                  }}
                  className="px-4 py-2 text-sm text-white rounded-lg cursor-pointer hover:bg-white/20"
                >
                  {ch}
                </div>
              ))}

              {/* Add new channel */}
              <div className="pt-2 mt-2 border-t border-white/20">
                <div
                  onClick={() => {
                    alert("Add new channel placeholder");
                    setDropdownOpen(false);
                  }}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-blue-300 rounded-lg cursor-pointer hover:bg-white/20"
                >
                  <PlusCircle className="w-4 h-4" />
                  <span>Add new channel</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Logout Button */}
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
