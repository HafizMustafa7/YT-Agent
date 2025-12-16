import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import PricingPage from './components/PricingPage'
import CheckoutPage from './components/CheckoutPage'
import SuccessPage from './components/SuccessPage'
import './App.css'

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<PricingPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/success" element={<SuccessPage />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App

