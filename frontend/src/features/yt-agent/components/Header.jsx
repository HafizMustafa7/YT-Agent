import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Sun, Moon, Menu, X, Settings, LogOut } from 'lucide-react';
import { useTheme } from '../../../contexts/ThemeContext';
import { tokenService } from '../../../services/tokenService';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import '../styles/components/Header.css';

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { isDarkTheme, toggleTheme } = useTheme();

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);

  const isDashboard = location.pathname === '/dashboard';
  const isAuth = location.pathname === '/auth';
  const isWelcome = location.pathname === '/';

  const showBackButton = !isDashboard && !isAuth && !isWelcome;
  const showSettings = !isAuth && !isWelcome;

  const handleLogout = async () => {
    await tokenService.logout();
  };

  return (
    <header className="header" role="banner">
      <div className="header-content">
        <div className="header-left">
          {showBackButton && (
            <button
              className="back-nav-btn"
              onClick={() => navigate(-1)}
              aria-label="Go back"
            >
              <ArrowLeft size={20} />
              <span>Back</span>
            </button>
          )}
          <h1 className="logo" onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }}>
            AI Trend Analyzer
          </h1>
        </div>

        <div className="header-right">
          <nav role="navigation" className={isMenuOpen ? 'active' : ''}>
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); navigate('/dashboard'); setIsMenuOpen(false); }}
              className={isDashboard ? 'active' : ''}
            >
              Dashboard
            </a>
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); navigate('/analytics'); setIsMenuOpen(false); }}
              className={location.pathname === '/analytics' ? 'active' : ''}
            >
              Analytics
            </a>
          </nav>

          <div className="header-actions">
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {isDarkTheme ? <Sun size={20} /> : <Moon size={20} />}
            </button>

            {showSettings && (
              <Dialog>
                <DialogTrigger asChild>
                  <button className="settings-btn" aria-label="Open settings">
                    <Settings size={20} />
                  </button>
                </DialogTrigger>
                <DialogContent className={`${isDarkTheme ? 'bg-slate-900 border-white/10' : 'bg-white border-slate-200'} rounded-2xl`}>
                  <DialogHeader>
                    <DialogTitle className={isDarkTheme ? 'text-white' : 'text-slate-900'}>Account Settings</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-6 pt-4">
                    <div className="flex flex-col gap-4">
                      <p className={`text-sm ${isDarkTheme ? 'text-slate-400' : 'text-slate-500'}`}>
                        Manage your account and preferences.
                      </p>
                      <Button
                        variant="destructive"
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 justify-center"
                      >
                        <LogOut size={18} />
                        Logout
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </div>

          <div className={`hamburger ${isMenuOpen ? 'active' : ''} `} onClick={toggleMenu} role="button" aria-label="Toggle navigation menu" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && toggleMenu()}>
            {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;