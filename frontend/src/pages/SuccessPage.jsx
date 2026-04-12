/**
 * SuccessPage — shown after successful Paddle payment
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import PageLayout from '../components/PageLayout';
import Header from '../features/yt-agent/components/Header';
import { Button } from '../components/ui/button';
import api from '../api/auth';

const SuccessPage = () => {
    const navigate = useNavigate();
    const { isDarkTheme } = useTheme();
    const [searchParams] = useSearchParams();

    const [status, setStatus] = useState('verifying'); // verifying, success, error
    const [errorMessage, setErrorMessage] = useState('');

    useEffect(() => {
        const verifyTransaction = async () => {
            // Paddle usually appends _ptxn to the redirect URL, but we also saved it in sessionStorage
            const urlTxnId = searchParams.get('_ptxn');
            const sessionTxnId = sessionStorage.getItem('paddle_transaction_id');
            const transactionId = urlTxnId || sessionTxnId;

            if (!transactionId) {
                setStatus('error');
                setErrorMessage('No transaction ID found. If you just paid, your credits will be added via webhook shortly.');
                return;
            }

            try {
                const response = await api.post('/api/paddle/verify', {
                    transaction_id: transactionId
                });

                if (response.data?.status === 'success' || response.data?.status === 'already_processed') {
                    setStatus('success');
                    sessionStorage.removeItem('paddle_transaction_id'); // cleanup
                    
                    // Auto redirect after 5 seconds on success
                    setTimeout(() => navigate('/dashboard'), 5000);
                } else {
                    setStatus('error');
                    setErrorMessage(response.data?.message || 'Verification is pending. Please check back later.');
                }
            } catch (err) {
                console.error('[SUCCESS_PAGE] Verification failed:', err);
                setStatus('error');
                setErrorMessage(err.response?.data?.detail || 'Failed to verify payment with the server.');
            }
        };

        verifyTransaction();
    }, [navigate, searchParams]);

    return (
        <PageLayout>
            <Header />
            <main className="flex items-center justify-center min-h-[70vh] px-8">
                <div className="text-center max-w-md">
                    {status === 'verifying' && (
                        <>
                            <div className="text-6xl mb-6 flex justify-center">
                                <svg className="animate-spin h-14 w-14 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            </div>
                            <h1 className={`text-2xl font-bold mb-3 ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
                                Verifying Payment...
                            </h1>
                            <p className={isDarkTheme ? 'text-slate-400' : 'text-slate-500'}>
                                Please wait while we confirm your transaction and add credits to your account.
                            </p>
                        </>
                    )}

                    {status === 'success' && (
                        <>
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
                        </>
                    )}

                    {status === 'error' && (
                        <>
                            <div className="text-7xl mb-6">⏳</div>
                            <h1 className={`text-2xl font-bold mb-3 ${isDarkTheme ? 'text-white' : 'text-slate-900'}`}>
                                Verification Pending
                            </h1>
                            <p className={`text-base mb-6 ${isDarkTheme ? 'text-slate-300' : 'text-slate-600'}`}>
                                {errorMessage}
                            </p>
                            <Button
                                onClick={() => navigate('/dashboard')}
                                className={isDarkTheme ? 'bg-slate-700 hover:bg-slate-600 text-white' : 'bg-slate-200 hover:bg-slate-300 text-slate-900'}
                            >
                                Return to Dashboard
                            </Button>
                        </>
                    )}
                </div>
            </main>
        </PageLayout>
    );
};

export default SuccessPage;
