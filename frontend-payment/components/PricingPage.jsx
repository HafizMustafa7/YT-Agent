import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PricingCard from './PricingCard'
import CreditCard from './CreditCard'
import APICosts from './APICosts'
import { pricingAPI } from '../services/api'
import './PricingPage.css'

const PricingPage = () => {
  const [pricingData, setPricingData] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    loadPricingData()
  }, [])

  const loadPricingData = async () => {
    try {
      const data = await pricingAPI.getPricingConfig()
      setPricingData(data)
    } catch (error) {
      // Fallback to demo data if API fails
      setPricingData(generateDemoData())
    } finally {
      setLoading(false)
    }
  }

  const generateDemoData = () => {
    return {
      credit_packages: [
        {
          name: "Starter Pack",
          credits: 20,
          bonus_credits: 0,
          total_credits: 20,
          price: 15.00,
          price_per_credit: 0.75,
          validity_days: 90
        },
        {
          name: "Creator Pack",
          credits: 60,
          bonus_credits: 0,
          total_credits: 60,
          price: 42.00,
          price_per_credit: 0.70,
          validity_days: 180
        },
        {
          name: "Professional Pack",
          credits: 100,
          bonus_credits: 0,
          total_credits: 100,
          price: 70.00,
          price_per_credit: 0.70,
          validity_days: 365
        }
      ],
      api_costs: [
        {
          api_name: "YouTube Data API",
          cost_per_call: 0.01,
          description: "Fetch video metadata, statistics, and channel information",
          included_in_tiers: []
        },
        {
          api_name: "YouTube Analytics API",
          cost_per_call: 0.02,
          description: "Advanced analytics and reporting data",
          included_in_tiers: []
        },
        {
          api_name: "OpenAI GPT-4 Analysis",
          cost_per_call: 0.15,
          description: "AI-powered content analysis and insights",
          included_in_tiers: []
        },
        {
          api_name: "Sentiment Analysis API",
          cost_per_call: 0.05,
          description: "Analyze comments and audience sentiment",
          included_in_tiers: []
        },
        {
          api_name: "Computer Vision API",
          cost_per_call: 0.08,
          description: "Thumbnail performance and visual analysis",
          included_in_tiers: []
        }
      ]
    }
  }

  const handleBuyCredits = (packageName) => {
    navigate(`/checkout?package=${encodeURIComponent(packageName)}`)
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading pricing plans...</p>
      </div>
    )
  }

  if (!pricingData) {
    return <div className="error-container">Failed to load pricing data</div>
  }

  return (
    <div className="pricing-page">
      <div className="container">
        <div className="header">
          <h1>Buy Packages</h1>
          <p>Pay only for what you use. Simple, transparent pricing.</p>
        </div>

        <div className="credits-section">
          <div className="credit-packages-grid">
            {pricingData.credit_packages.map((pkg) => (
              <CreditCard
                key={pkg.name}
                package={pkg}
                onBuy={() => handleBuyCredits(pkg.name)}
              />
            ))}
          </div>
        </div>

        <APICosts apiCosts={pricingData.api_costs} />
      </div>
    </div>
  )
}

export default PricingPage


