import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import Starfield from './Starfield';

const PageLayout = ({ children, className = "" }) => {
    const { isDarkTheme } = useTheme();

    const backgroundClass = isDarkTheme
        ? "bg-gradient-to-br from-slate-900 via-blue-900 to-purple-900 text-white"
        : "bg-white text-black";

    return (
        <div className={`min-h-screen relative overflow-hidden transition-colors duration-500 ${backgroundClass} ${className}`}>
            {isDarkTheme && <Starfield />}
            <div className="relative z-10 w-full">
                {children}
            </div>
        </div>
    );
};

export default PageLayout;
