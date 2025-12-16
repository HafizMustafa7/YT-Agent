import React from 'react'
import './APICosts.css'

const APICosts = ({ apiCosts }) => {
  return (
    <div className="api-costs">
      <h2>API Usage & Costs</h2>
      <p className="api-costs-description">
        Transparent pricing for all external API calls used in video analysis
      </p>
      <div className="api-grid">
        {apiCosts.map((api, index) => (
          <div key={index} className="api-card">
            <div className="api-name">{api.api_name}</div>
            <div className="api-cost">
              ${api.cost_per_call.toFixed(2)}
              <span> per call</span>
            </div>
            <div className="api-description">{api.description}</div>
            <div className="included-tiers">
              <strong>Included in:</strong>{' '}
              {api.included_in_tiers
                .map((tier) => tier.charAt(0).toUpperCase() + tier.slice(1))
                .join(', ')}{' '}
              plans
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default APICosts


