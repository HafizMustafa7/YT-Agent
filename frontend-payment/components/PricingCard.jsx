import React from 'react'
import './PricingCard.css'

const PricingCard = ({ tier, isYearly, onSelect }) => {
  const price = isYearly ? tier.yearly_price : tier.monthly_price
  const interval = isYearly ? 'year' : 'month'
  const isFeatured = tier.level === 'pro'

  return (
    <div className={`pricing-card ${isFeatured ? 'featured' : ''}`}>
      {isFeatured && <div className="popular-badge">MOST POPULAR</div>}
      <div className="plan-name">{tier.name}</div>
      <div className="plan-price">
        ${price.toFixed(2)}
        <span>/{interval}</span>
      </div>
      {isYearly && (
        <div className="plan-savings">
          Save ${tier.yearly_savings?.toFixed(2) || 0}/year
        </div>
      )}
      <div className="plan-interval">
        {tier.videos_per_month === 'unlimited' || tier.videos_per_month === -1
          ? 'Unlimited'
          : tier.videos_per_month}{' '}
        videos per month
      </div>
      <ul className="plan-features">
        {tier.features.map((feature, index) => (
          <li key={index}>{feature}</li>
        ))}
      </ul>
      <button className="plan-button" onClick={onSelect}>
        Get Started
      </button>
    </div>
  )
}

export default PricingCard


