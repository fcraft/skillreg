/**
 * SSH API client
 */

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(data.error || res.statusText)
  }
  return res.json()
}

function get(path) { return request(path) }
function post(path, body) { return request(path, { method: 'POST', body: JSON.stringify(body) }) }
function put(path, body) { return request(path, { method: 'PUT', body: JSON.stringify(body) }) }
function del(path) { return request(path, { method: 'DELETE' }) }

// Host CRUD
export function fetchHosts()        { return get('/api/ssh/hosts') }
export function addHost(body)       { return post('/api/ssh/hosts', body) }
export function updateHost(id, body) { return put(`/api/ssh/hosts/${encodeURIComponent(id)}`, body) }
export function deleteHost(id)      { return del(`/api/ssh/hosts/${encodeURIComponent(id)}`) }

// Connection check
export function checkHost(id)       { return post(`/api/ssh/hosts/${encodeURIComponent(id)}/check`) }

// Remote skill operations
export function getHostStatus(id)         { return get(`/api/ssh/hosts/${encodeURIComponent(id)}/status`) }
export function syncHost(id, body)        { return post(`/api/ssh/hosts/${encodeURIComponent(id)}/sync`, body || {}) }
export function listHostSkills(id)        { return get(`/api/ssh/hosts/${encodeURIComponent(id)}/skills`) }
export function bootstrapHost(id)         { return post(`/api/ssh/hosts/${encodeURIComponent(id)}/bootstrap`) }
export function installHost(id)           { return post(`/api/ssh/hosts/${encodeURIComponent(id)}/install`) }
export function getHostConfig(id)         { return get(`/api/ssh/hosts/${encodeURIComponent(id)}/config`) }
export function updateHostConfig(id, cfg) { return put(`/api/ssh/hosts/${encodeURIComponent(id)}/config`, cfg) }
export function getStructuredStatus(id)   { return get(`/api/ssh/hosts/${encodeURIComponent(id)}/structured-status`) }
