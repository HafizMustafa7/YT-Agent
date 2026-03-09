/**
 * CheckoutPage — integrated into main frontend
 * Reads package from URL params, initiates Paddle checkout using JWT from Supabase session.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import PageLayout from '../components/PageLayout';
import Header from '../features/yt-agent/components/Header';
import { Button } from '../components/ui/button';
import { supabase } from '../supabaseClient';
import api from '../api/auth';

// Load Paddle.js once
const initializePaddle = () =>
    new Promise((resolve) => {
        if (window.Paddle) { resolve(window.Paddle); return; }
        const script = document.createElement('script');
        script.src = 'https://cdn.paddle.com/paddle/v2/paddle.js';
        script.async = true;
        script.onload = () => {
            if (window.Paddle) {
                const env = import.meta.env.VITE_PADDLE_ENVIRONMENT || 'sandbox';
                const token = import.meta.env.VITE_PADDLE_CLIENT_TOKEN || 'test_fd9e78a92d5bc0c7f69d021fc39';
                window.Paddle.Environment.set(env);
                window.Paddle.Initialize({ token });
                resolve(window.Paddle);
            }
        };
        document.body.appendChild(script);
    });

const CheckoutPage = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { isDarkTheme } = useTheme();

    const packageName = searchParams.get('package');
    const packageId = searchParams.get('package_id');

    const [loading, setLoading] = useState(false);
    const [paddleReady, setPaddleReady] = useState(false);
    const [error, setError] = useState(null);
    const [pkg, setPkg] = useState(null);

    useEffect(() => {
        initializePaddle().then(() => setPaddleReady(true));
        fetchPackage();
    }, []);

    const fetchPackage = async () => {
        if (!packageId) return;
        try {
            const res = await api.get('/api/pricing');
            const found = (res.data.packages || []).find((p) => p.id === packageId);
            if (found) setPkg(found);
        } catch (err) {
            console.error('[CHECKOUT] Failed to load package:', err);
        }
    };

    const handleCheckout = async () => {
        if (!paddleReady) {
            setError('Payment system is still loading. Please try again.');
            return;
        }
        if (!packageId) {
            setError('No package selected. Please go back and select a package.');
            return;
        }

        const { data: { session } } = await supabase.auth.getSession();
        if (!session?.access_token) {
            setError('You must be logged in to make a purchase.');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await api.post('/api/paddle/create-checkout', {
                package_id: packageId,
                success_url: `${window.location.origin}/success`,
                cancel_url: `${window.location.origin}/pricing`,
            });

            if (response.data?.transactionId && window.Paddle) {
                window.Paddle.Checkout.open({ transactionId: response.data.transactionId });
            } else {
                setError('Failed to initialize checkout — missing transaction ID. Please try again.');
            }
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || 'Failed to create order. Please try again.';
            setError(detail);
        } finally {
            setLoading(false);
        }
    };

    const displayPackage = pkg || { name: packageName, price: '—', credits: '—' };

    return (
        <PageLayout>
            <Header />
            <main className="relative z-10 flex items-center justify-center min-h-[70vh] px-8 py-12">
                <div className={`w-full max-w-md rounded-2xl border shadow-2xl p-8 ${isDarkTheme ? 'bg-slate-800/90 border-white/10' : 'bg-white border-slate-200'
                    }`}>
                    <button
                        className={`text-sm mb-6 flex items-center gap-1 ${isDarkTheme ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-900'}`}
                        onClick={() => navigate('/pricing')}
                    >
                        ← Back to Pricing
                    </button>

                    <h1 className={`text-2xl font-bold mb-6 ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
                        Review Order
                    </h1>

                    {/* Order Summary */}
                    <div className={`rounded-xl p-5 mb-6 ${isDarkTheme ? 'bg-slate-700/60' : 'bg-slate-50'}`}>
                        <div className="flex justify-between mb-3">
                            <span className={isDarkTheme ? 'text-slate-400' : 'text-slate-500'}>Package</span>
                            <span className={`font-semibold ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>{displayPackage.name}</span>
                        </div>
                        <div className="flex justify-between mb-3">
                            <span className={isDarkTheme ? 'text-slate-400' : 'text-slate-500'}>Credits</span>
                            <span className={`font-semibold ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>{displayPackage.credits}</span>
                        </div>
                        <div className={`flex justify-between pt-3 border-t ${isDarkTheme ? 'border-white/10' : 'border-slate-200'}`}>
                            <span className={`font-bold ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>Total</span>
                            <span className={`text-xl font-bold ${isDarkTheme ? 'text-cyan-400' : 'text-indigo-600'}`}>
                                {displayPackage.price !== '—' ? `$${Number(displayPackage.price).toFixed(2)}` : '—'}
                            </span>
                        </div>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 text-sm">
                            {error}
                        </div>
                    )}

                    <Button
                        onClick={handleCheckout}
                        disabled={loading || !packageId}
                        className={`w-full py-6 text-base font-semibold ${isDarkTheme
                            ? 'bg-gradient-to-r from-cyan-500 to-purple-600 hover:opacity-90'
                            : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                            }`}
                    >
                        {loading ? 'Processing…' : '🔒 Proceed to Secure Checkout'}
                    </Button>

                    <p className={`text-xs text-center mt-4 ${isDarkTheme ? 'text-slate-500' : 'text-slate-400'}`}>
                        Powered by Paddle · PCI-Compliant · Secure Payment
                    </p>
                </div>
            </main>
        </PageLayout>
    );
};

export default CheckoutPage;
