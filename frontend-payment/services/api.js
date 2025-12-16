import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const pricingAPI = {
  getPricingConfig: async () => {
    try {
      const response = await api.get('/api/pricing/config')
      return response.data
    } catch (error) {
      console.error('Error fetching pricing config:', error)
      throw error
    }
  },

  createSubscription: async (subscriptionData) => {
    try {
      const response = await api.post('/api/subscriptions', subscriptionData)
      return response.data
    } catch (error) {
      console.error('Error creating subscription:', error)
      throw error
    }
  },

  purchaseCredits: async (creditData) => {
    try {
      const response = await api.post('/api/credits', creditData)
      return response.data
    } catch (error) {
      console.error('Error purchasing credits:', error)
      throw error
    }
  },

  createUser: async (userData) => {
    try {
      const response = await api.post('/api/users', userData)
      return response.data
    } catch (error) {
      console.error('Error creating user:', error)
      throw error
    }
  },


  processPayment: async (paymentData) => {
    try {
      const response = await api.post('/api/payments/process', paymentData)
      return response.data
    } catch (error) {
      console.error('Error processing payment:', error)
      throw error
    }
  },

  initiatePayment: async (data) => {
    try {
      const response = await api.post('/api/paddle/create-checkout', data)
      return response.data
    } catch (error) {
      console.error('Error initiating payment:', error)
      throw error
    }
  }
}

export default api


