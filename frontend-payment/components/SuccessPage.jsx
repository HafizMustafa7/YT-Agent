import React from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import './SuccessPage.css'

const SuccessPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const type = searchParams.get('type')
  const amount = searchParams.get('amount')

  return (
    <div className="success-page">
      <div className="success-container">
        <div className="success-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="#10b981" strokeWidth="2" fill="none"/>
            <path d="M8 12l2 2 4-4" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <h1>Payment Successful!</h1>
        <p className="success-message">
          Your {type === 'subscription' ? 'subscription' : 'credits'} has been activated successfully.
        </p>
        {amount && (
          <p className="success-amount">Amount Paid: ${amount}</p>
        )}
        <div className="success-actions">
          <button className="primary-button" onClick={() => navigate('/')}>
            Back to Plans
          </button>
          <button className="secondary-button" onClick={() => window.location.href = '/'}>
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}

export default SuccessPage


