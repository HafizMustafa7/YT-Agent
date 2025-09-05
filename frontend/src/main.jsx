import React, { createContext, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App";
import axios from "axios";

axios.defaults.withCredentials = true;

// ✅ Create a global context for auth/session and selected channel
export const AppContext = createContext(null);

function AppProvider({ children }) {
  const [selectedChannel, setSelectedChannel] = useState(null);

  return (
    <AppContext.Provider value={{ selectedChannel, setSelectedChannel }}>
      {children}
    </AppContext.Provider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppProvider>
        <App />
      </AppProvider>
    </BrowserRouter>
  </React.StrictMode>
);
