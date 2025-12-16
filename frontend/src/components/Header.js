import React, { useState } from 'react';
import '../styles/components/Header.css';

const Header = ({ currentView }) => {  // Optional prop for active state
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);

  return (
    <header className="header" role="banner">
      <div className="header-content">
        <h1 className="logo">AI Trend Analyzer</h1>
        <nav role="navigation" className={isMenuOpen ? 'active' : ''}>
          <a
            href="#home"
            onClick={() => { window.scrollTo(0, 0); setIsMenuOpen(false); }}
            className={currentView === 'home' ? 'active' : ''}
          >
            Home
          </a>
          {/* Add more links if needed, e.g., <a href="#about">About</a> */}
        </nav>
        <div className={`hamburger ${isMenuOpen ? 'active' : ''} `} onClick={toggleMenu} role="button" aria-label="Toggle navigation menu" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && toggleMenu()}>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </header>
  );
};

export default Header;