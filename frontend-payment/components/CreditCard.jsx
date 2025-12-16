import React from 'react'
import './CreditCard.css'

const CreditCard = ({ package: pkg, onBuy }) => {
  return (
    <div className="credit-card">
      <div className="credit-header">
        <div className="credit-name">{pkg.name}</div>
        <div className="credit-amount">
          {pkg.total_credits}
          <span> credits</span>
        </div>
        {pkg.bonus_credits > 0 && (
          <div className="bonus-badge">+{pkg.bonus_credits} BONUS</div>
        )}
      </div>
      <div className="credit-price">${pkg.price.toFixed(2)}</div>
      <div className="credit-details">
        <p>
          <strong>Per Credit:</strong> ${pkg.price_per_credit.toFixed(2)}
        </p>
        <p>
          <strong>Valid For:</strong> {pkg.validity_days} days
        </p>
        <p>
          <strong>Base Credits:</strong> {pkg.credits}
        </p>
      </div>
      <button className="credit-button" onClick={onBuy}>
        Buy Now
      </button>
    </div>
  )
}

export default CreditCard


