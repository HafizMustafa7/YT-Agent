/**
 * PricingPage — integrated into main frontend
 * Uses supabase session for auth, fetches packages from backend DB.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import PageLayout from '../components/PageLayout';
import Header from '../features/yt-agent/components/Header';
import { Button } from '../components/ui/button';
import api from '../api/auth';

const PricingPage = () => {
    const [packages, setPackages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { isDarkTheme } = useTheme();
    const navigate = useNavigate();

    useEffect(() => {
        fetchPackages();
    }, []);

    const fetchPackages = async () => {
        try {
            const res = await api.get('/api/pricing');
            setPackages(res.data.packages || []);
        } catch (err) {
            console.error('[PRICING] Failed to load packages:', err);
            setError('Failed to load pricing. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleBuy = (pkg) => {
        navigate(`/checkout?package=${encodeURIComponent(pkg.name)}&package_id=${pkg.id}`);
    };

    return (
        <PageLayout>
            <Header />
            <main className="relative z-10 px-8 py-12 mx-auto max-w-5xl">
                <div className="text-center mb-12">
                    <h1 className={`text-4xl font-bold mb-3 ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
                        Buy Credits
                    </h1>
                    <p className={`text-lg ${isDarkTheme ? 'text-slate-300' : 'text-slate-600'}`}>
                        1 credit = 4 seconds of AI-generated video. Pay once, use anytime.
                    </p>
                </div>

                {loading && (
                    <div className="flex justify-center py-20">
                        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                )}

                {error && (
                    <div className="text-center py-10">
                        <p className="text-red-500 mb-4">{error}</p>
                        <Button onClick={fetchPackages}>Retry</Button>
                    </div>
                )}

                {!loading && !error && (
                    <div className="grid gap-8 sm:grid-cols-3">
                        {packages.map((pkg) => (
                            <div
                                key={pkg.id}
                                className={`flex flex-col rounded-2xl border p-8 shadow-lg transition-all duration-300 hover:scale-105 ${isDarkTheme
                                        ? 'bg-slate-800/80 border-white/10 hover:border-cyan-500/50'
                                        : 'bg-white border-slate-200 hover:border-indigo-500/50'
                                    }`}
                            >
                                <h2 className={`text-xl font-bold mb-2 ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
                                    {pkg.name}
                                </h2>
                                {pkg.description && (
                                    <p className={`text-sm mb-4 flex-grow ${isDarkTheme ? 'text-slate-400' : 'text-slate-500'}`}>
                                        {pkg.description}
                                    </p>
                                )}
                                <div className="my-4">
                                    <span className={`text-4xl font-extrabold ${isDarkTheme ? 'text-cyan-400' : 'text-indigo-600'}`}>
                                        ${Number(pkg.price).toFixed(2)}
                                    </span>
                                </div>
                                <div className={`mb-6 text-sm ${isDarkTheme ? 'text-slate-300' : 'text-slate-600'}`}>
                                    <span className="font-semibold">{pkg.credits}</span> credits included
                                    <span className={`ml-2 text-xs ${isDarkTheme ? 'text-slate-500' : 'text-slate-400'}`}>
                                        (~{Math.floor(pkg.credits * 4 / 60)} min of video)
                                    </span>
                                </div>
                                <Button
                                    onClick={() => handleBuy(pkg)}
                                    className={`w-full mt-auto ${isDarkTheme
                                        ? 'bg-gradient-to-r from-cyan-500 to-purple-600 hover:opacity-90'
                                        : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                                        }`}
                                >
                                    Get Started
                                </Button>
                            </div>
                        ))}
                    </div>
                )}

                {!loading && !error && packages.length === 0 && (
                    <p className={`text-center py-16 ${isDarkTheme ? 'text-slate-400' : 'text-slate-500'}`}>
                        No packages available at the moment. Please check back later.
                    </p>
                )}
            </main>
        </PageLayout>
    );
};

export default PricingPage;
