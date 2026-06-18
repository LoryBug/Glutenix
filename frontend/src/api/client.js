import axios from 'axios'

const api = axios.create({ baseURL: '' })

export function getHealth() { return api.get('/health').then(r => r.data) }

export function listIngredients() { return api.get('/ingredients').then(r => r.data) }
export function getIngredient(id) { return api.get(`/ingredients/${id}`).then(r => r.data) }
export function createIngredient(data) { return api.post('/ingredients', data).then(r => r.data) }
export function updateIngredient(id, data) { return api.put(`/ingredients/${id}`, data).then(r => r.data) }
export function deleteIngredient(id) { return api.delete(`/ingredients/${id}`) }

export function listApplications() { return api.get('/applications').then(r => r.data) }
export function getApplication(id) { return api.get(`/applications/${id}`).then(r => r.data) }

export function listBlends() { return api.get('/blends').then(r => r.data) }
export function getBlend(id) { return api.get(`/blends/${id}`).then(r => r.data) }
export function createBlend(data) { return api.post('/blends', data).then(r => r.data) }
export function deleteBlend(id) { return api.delete(`/blends/${id}`) }

export function simulate(data) { return api.post('/simulate', data).then(r => r.data) }
export function listSimulations() { return api.get('/simulate').then(r => r.data) }

export function simulateSweep(data) { return api.post('/simulate/sweep', data).then(r => r.data) }
export function listSweepTargetProfiles() { return api.get('/simulate/target-profiles').then(r => r.data) }

export function predict(data) { return api.post('/predict', data).then(r => r.data) }

export function getARD() { return api.get('/optimize/ard').then(r => r.data) }

export default api
