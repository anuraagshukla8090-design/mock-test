import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Log errors to console (debug tool — no fancy toasts needed)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[API Error]', err.config?.url, err.response?.status, err.response?.data)
    return Promise.reject(err)
  }
)

export default api
