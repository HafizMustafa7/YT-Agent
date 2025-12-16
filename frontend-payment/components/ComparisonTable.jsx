import React from 'react'
import './ComparisonTable.css'

const ComparisonTable = ({ tiers }) => {
  const features = [
    {
      name: 'Videos per Month',
      basic: tiers.find((t) => t.level === 'basic')?.videos_per_month || 50,
      pro: tiers.find((t) => t.level === 'pro')?.videos_per_month || 200,
      enterprise:
        tiers.find((t) => t.level === 'enterprise')?.videos_per_month ||
        'Unlimited',
    },
    {
      name: 'API Calls Limit',
      basic: tiers.find((t) => t.level === 'basic')?.api_calls_limit || 1000,
      pro: tiers.find((t) => t.level === 'pro')?.api_calls_limit || 5000,
      enterprise:
        tiers.find((t) => t.level === 'enterprise')?.api_calls_limit ||
        'Unlimited',
    },
    {
      name: 'Team Members',
      basic: tiers.find((t) => t.level === 'basic')?.team_members || 1,
      pro: tiers.find((t) => t.level === 'pro')?.team_members || 3,
      enterprise:
        tiers.find((t) => t.level === 'enterprise')?.team_members ||
        'Unlimited',
    },
    {
      name: 'Data Retention',
      basic:
        tiers.find((t) => t.level === 'basic')?.analytics_retention_days ||
        '7 days',
      pro:
        tiers.find((t) => t.level === 'pro')?.analytics_retention_days ||
        '30 days',
      enterprise: 'Unlimited',
    },
    {
      name: 'Basic Analytics',
      basic: true,
      pro: true,
      enterprise: true,
    },
    {
      name: 'AI-Powered Insights',
      basic: false,
      pro: true,
      enterprise: true,
    },
    {
      name: 'Competitor Analysis',
      basic: false,
      pro: true,
      enterprise: true,
    },
    {
      name: 'Custom Branding',
      basic: false,
      pro: false,
      enterprise: true,
    },
    {
      name: 'Priority Support',
      basic: false,
      pro: true,
      enterprise: true,
    },
    {
      name: 'Dedicated Account Manager',
      basic: false,
      pro: false,
      enterprise: true,
    },
  ]

  return (
    <div className="comparison-table">
      <h2>Feature Comparison</h2>
      <table>
        <thead>
          <tr>
            <th>Feature</th>
            <th>Basic</th>
            <th>Pro</th>
            <th>Enterprise</th>
          </tr>
        </thead>
        <tbody>
          {features.map((feature, index) => (
            <tr key={index}>
              <td>
                <strong>{feature.name}</strong>
              </td>
              <td>
                {typeof feature.basic === 'boolean' ? (
                  feature.basic ? (
                    <span className="check-icon">✓</span>
                  ) : (
                    <span className="cross-icon">✗</span>
                  )
                ) : (
                  feature.basic
                )}
              </td>
              <td>
                {typeof feature.pro === 'boolean' ? (
                  feature.pro ? (
                    <span className="check-icon">✓</span>
                  ) : (
                    <span className="cross-icon">✗</span>
                  )
                ) : (
                  feature.pro
                )}
              </td>
              <td>
                {typeof feature.enterprise === 'boolean' ? (
                  feature.enterprise ? (
                    <span className="check-icon">✓</span>
                  ) : (
                    <span className="cross-icon">✗</span>
                  )
                ) : (
                  feature.enterprise
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ComparisonTable


