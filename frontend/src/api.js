import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default api

/* -----------------------------
 *  Endpoint helpers
 * ----------------------------- */

export const apiHealth = () => api.get('/health')

// Farmer flow
export const createHealthReport = (formData, config = {}) =>
  api.post('/health-reports', formData, config)

// Reports
export const getHealthReport = (reportId) =>
  api.get(`/health-reports/${reportId}`)

export const getReportComparison = (reportId) =>
  api.get(`/health-reports/${reportId}/comparison`)

export const getReportFollowUps = (reportId) =>
  api.get(`/health-reports/${reportId}/follow-ups`)

export const scheduleFollowUp = (reportId, payload) =>
  api.post(`/health-reports/${reportId}/follow-up`, payload)

// Expert validation
export const submitExpertValidation = (reportId, payload) =>
  api.post(`/health-reports/${reportId}/expert-validation`, payload)

export const getExpertValidations = (reportId) =>
  api.get(`/health-reports/${reportId}/expert-validation`)

// Officer queue
export const getOfficerQueue = (params = {}) =>
  api.get('/expert-review/queue', { params })

// Hotspots
export const getHotspots = (params = {}) =>
  api.get('/hotspots', { params })

export const getHotspotsNear = (params) =>
  api.get('/hotspots/near', { params })

// Reference data
export const createFarmer = (payload) => api.post('/farmers', payload)
export const createFarm = (payload) => api.post('/farms', payload)
export const createCrop = (payload) => api.post('/crops', payload)
export const createCropSeason = (payload) =>
  api.post('/crop-seasons', payload)