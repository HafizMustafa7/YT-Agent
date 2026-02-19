import React, { createContext, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App";
import axios from "axios";

axios.defaults.withCredentials = true;

import { SelectedChannelProvider } from "./contexts/SelectedChannelContext";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <SelectedChannelProvider>
        <App />
      </SelectedChannelProvider>
    </BrowserRouter>
  </React.StrictMode>
);
