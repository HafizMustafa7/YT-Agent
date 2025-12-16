import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { pricingAPI } from '../services/api'
import './CheckoutPage.css'

// Load Paddle.js
const initializePaddle = () => {
  return new Promise((resolve) => {
    if (window.Paddle) {
      resolve(window.Paddle)
      return
    }
    const script = document.createElement('script')
    script.src = 'https://cdn.paddle.com/paddle/v2/paddle.js'
    script.async = true
    script.onload = () => {
      if (window.Paddle) {
        // Initialize with your Paddle client token
        window.Paddle.Environment.set('sandbox') // Change to 'production' for live
        window.Paddle.Initialize({
          token: 'test_fd9e78a92d5bc0c7f69d021fc39' // You'll need to add your Paddle client-side token here
        })
        resolve(window.Paddle)
      }
    }
    document.body.appendChild(script)
  })
}

const CheckoutPage = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [pricingData, setPricingData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [paddleReady, setPaddleReady] = useState(false)



  const packageName = searchParams.get('package')

  useEffect(() => {
    loadPricing()
    initializePaddle().then(() => setPaddleReady(true))
  }, [])

  const loadPricing = async () => {
    try {
      const config = await pricingAPI.getPricingConfig()
      setPricingData(config)
    } catch (err) {
      console.error('Error loading config:', err)
      setError('Failed to load pricing configuration.')
    } finally {
      setLoading(false)
    }
  }

  const getSelectedItem = () => {
    if (!pricingData) return null
    // Check credit packages
    const creditPkg = pricingData.credit_packages?.find(p => p.name === packageName)
    if (creditPkg) return { ...creditPkg, type: 'credit' }

    // Check subscription packages
    const subPkg = pricingData.subscription_packages?.find(p => p.name === packageName)
    if (subPkg) return { ...subPkg, type: 'subscription' }

    return null
  }

  const handleCreateOrder = async () => {
    setLoading(true)
    setError(null)

    console.log('\n' + '='.repeat(60))
    console.log('[CHECKOUT] Starting checkout process')
    console.log('='.repeat(60))

    if (!paddleReady) {
      const errorMsg = 'Payment system is still loading. Please try again.'
      console.error('[ERROR] Paddle not ready')
      setError(errorMsg)
      setLoading(false)
      return
    }

    console.log('[STEP 1] Paddle is ready')
    console.log('[STEP 2] Calling backend API to create checkout...')

    try {
      const requestData = {
        user_id: '1', // Placeholder: Replace with actual auth user ID from Supabase
        package_name: packageName,
        success_url: `${window.location.origin}/success`,
        cancel_url: `${window.location.origin}/checkout?package=${packageName}`
      }

      console.log('Request data:', requestData)

      const response = await pricingAPI.initiatePayment(requestData)

      console.log('[SUCCESS] Backend response received:', response)

      // Open Paddle checkout with the Transaction ID (Server-side creation)
      if (response && response.transactionId && window.Paddle) {
        console.log('[STEP 3] Opening Paddle checkout with Transaction ID...')
        console.log('Transaction ID:', response.transactionId)

        try {
          window.Paddle.Checkout.open({
            transactionId: response.transactionId
          })
          console.log('[SUCCESS] Paddle checkout opened')
        } catch (paddleError) {
          console.error('[PADDLE ERROR] Failed to open checkout:', paddleError)
          console.error('Error details:', {
            name: paddleError.name,
            message: paddleError.message,
            stack: paddleError.stack
          })
          setError(`Paddle checkout error: ${paddleError.message}`)
        }
      } else if (response.checkout_data) {
        // Fallback for legacy support if backend not updated
        console.warn('[WARN] Using legacy client-side checkout data object')
        window.Paddle.Checkout.open(response.checkout_data)
      } else {
        console.error('[ERROR] Missing transactionId')
        console.error('Response:', response)
        setError('Failed to initialize checkout - missing transaction ID')
      }
    } catch (err) {
      console.error('[API ERROR] Failed to create checkout:', err)
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status
      })

      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create order. Please try again.'
      setError(errorMessage)
    } finally {
      setLoading(false)
      console.log('='.repeat(60) + '\n')
    }
  }

  if (loading) {
    return <div className="loading-container"><div className="loading-spinner"></div><p>Loading...</p></div>
  }

  if (error && !pricingData) {
    return <div className="error-container">{error}</div>
  }

  const selectedItem = getSelectedItem()

  if (!selectedItem) {
    return <div className="error-container">Invalid selection. <button onClick={() => navigate('/')}>Go Back</button></div>
  }

  const price = selectedItem.price



  // VIEW: Order Review (Before creation)
  return (
    <div className="checkout-page">
      <div className="checkout-container">
        <div className="checkout-header">
          <h1>Review Order</h1>
          <button className="back-button" onClick={() => navigate('/')}>← Back</button>
        </div>

        <div className="checkout-content">
          <div className="order-summary">
            <h2>Order Summary</h2>
            <div className="summary-item">
              <div className="summary-label">Item</div>
              <div className="summary-value">
                {selectedItem.name}
                {selectedItem.type === 'subscription' && <span className="plan-interval"> ({selectedItem.interval})</span>}
              </div>
            </div>
            {selectedItem.type === 'credit' && (
              <div className="summary-item">
                <div className="summary-label">Credits</div>
                <div className="summary-value">{selectedItem.total_credits}</div>
              </div>
            )}
            <div className="summary-total">
              <div className="summary-label">Total</div>
              <div className="summary-value">${price.toFixed(2)}</div>
            </div>

          </div>

          <div className="payment-section">
            <h3>Secure Payment with Paddle</h3>
            <p className="payment-description">
              You will be redirected to Paddle's secure checkout page to complete your payment.
            </p>

            {error && <div className="error-message">{error}</div>}

            <button
              className="submit-button paddle-button"
              onClick={handleCreateOrder}
              disabled={loading}
            >
              {loading ? 'Processing...' : 'Proceed to Checkout'}
            </button>

            <div className="secure-badge">
              <span>🔒 PCI-Compliant Secure Payment</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CheckoutPage
