/**
 * SuccessPage — shown after successful Paddle payment
 */
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import PageLayout from '../components/PageLayout';
import Header from '../features/yt-agent/components/Header';
import { Button } from '../components/ui/button';

const SuccessPage = () => {
    const navigate = useNavigate();
    const { isDarkTheme } = useTheme();

    useEffect(() => {
        // Auto redirect after 5 seconds
        const timer = setTimeout(() => navigate('/dashboard'), 5000);
        return () => clearTimeout(timer);
    }, [navigate]);

    return (
        <PageLayout>
            <Header />
            <main className="flex items-center justify-center min-h-[70vh] px-8">
                <div className="text-center max-w-md">
                    <div className="text-7xl mb-6">🎉</div>
                    <h1 className={`text-3xl font-bold mb-3 ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
                        Payment Successful!
                    </h1>
                    <p className={`text-lg mb-2 ${isDarkTheme ? 'text-slate-300' : 'text-slate-600'}`}>
                        Your credits have been added to your account.
                    </p>
                    <p className={`text-sm mb-8 ${isDarkTheme ? 'text-slate-500' : 'text-slate-400'}`}>
                        Redirecting to dashboard in 5 seconds…
                    </p>
                    <Button
                        onClick={() => navigate('/dashboard')}
                        className={isDarkTheme ? 'bg-gradient-to-r from-cyan-500 to-purple-600' : 'bg-indigo-600 text-white hover:bg-indigo-700'}
                    >
                        Go to Dashboard
                    </Button>
                </div>
            </main>
        </PageLayout>
    );
};

export default SuccessPage;
