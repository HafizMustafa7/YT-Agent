// frontend/src/components/Header.js
import React from 'react';
import './Header.css';

const Header = () => {
  return (
    <header className="header">
      <h2 className="logo">TrendVision AI</h2>
      <nav className="nav">
        <a href="#features" className="nav-link">Features</a>
        <a href="#how-it-works" className="nav-link">How It Works</a>
        <a href="#pricing" className="nav-link">Pricing</a>
      </nav>
    </header>
  );
};

export default Header;