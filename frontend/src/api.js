import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 600000,
})

export default api

/* -----------------------------
 *  Endpoint helpers
 * ----------------------------- */

export const apiHealth = () => api.get('/health')

export const createHealthReport = (formData, config = {}) =>
  api.post('/health-reports', formData, config)

export const getHealthReport = (reportId) =>
  api.get(`/health-reports/${reportId}`)

export const getReportComparison = (reportId) =>
  api.get(`/health-reports/${reportId}/comparison`)

export const getReportFollowUps = (reportId) =>
  api.get(`/health-reports/${reportId}/follow-ups`)

export const scheduleFollowUp = (reportId, payload) =>
  api.post(`/health-reports/${reportId}/follow-up`, payload)

export const submitExpertValidation = (reportId, payload) =>
  api.post(`/health-reports/${reportId}/expert-validation`, payload)

export const getExpertValidations = (reportId) =>
  api.get(`/health-reports/${reportId}/expert-validation`)

export const getOfficerQueue = (params = {}) =>
  api.get('/expert-review/queue', { params })

export const getHotspots = (params = {}) =>
  api.get('/hotspots', { params })

export const getHotspotsNear = (params) =>
  api.get('/hotspots/near', { params })

export const createFarmer = (payload) => api.post('/farmers', payload)
export const createFarm = (payload) => api.post('/farms', payload)
export const createCrop = (payload) => api.post('/crops', payload)
export const createCropSeason = (payload) =>
  api.post('/crop-seasons', payload)