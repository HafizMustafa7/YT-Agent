import { supabase } from "../supabaseClient";
import apiService from "../features/yt-agent/services/apiService";

function ChannelSelector({ selectedChannel, setSelectedChannel }) {
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    const initializeSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || !session.user) {
          console.error("[CHANNEL SELECTOR] No session found");
          return;
        }
        setSessionReady(true);
        fetchChannels();
      } catch (err) {
        console.error("[CHANNEL SELECTOR] Session verification failed:", err);
      }
    };

    initializeSession();
  }, []);

  const fetchChannels = async () => {
    try {
      const data = await apiService.listChannels();
      setChannels(data || []);
    } catch (err) {
      console.error("Error fetching channels:", err);
    }
  };

  const handleAddChannel = async () => {
    try {
      setLoading(true);
      const data = await apiService.startYouTubeOAuth();
      if (data?.url) {
        window.location.href = data.url; // redirect to Google OAuth
      }
    } catch (err) {
      console.error("Error starting OAuth:", err);
      setLoading(false);
    }
  };

  return (
    <div className="mb-4">
      <label className="block mb-2 font-semibold">Select Channel:</label>
      <select
        value={selectedChannel || ""}
        onChange={(e) => setSelectedChannel(e.target.value)}
        className="w-full p-2 border rounded"
      >
        <option value="" disabled>
          -- Select a channel --
        </option>
        {channels.map((ch) => (
          <option key={ch.channel_id} value={ch.channel_id}>
            {ch.channel_name}
          </option>
        ))}
      </select>

      <button
        onClick={handleAddChannel}
        disabled={loading}
        className="px-4 py-2 mt-2 text-white bg-blue-600 rounded"
      >
        {loading ? "Redirecting..." : "Add Channel"}
      </button>
    </div>
  );
}

export default ChannelSelector;
