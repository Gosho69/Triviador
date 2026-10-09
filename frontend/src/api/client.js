const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

const NETWORK_ERROR = "Can't reach the server. Check your connection and try again."
const UNKNOWN_ERROR = 'Something went wrong. Please try again.'

export class ApiError extends Error {
  constructor(status, errors) {
    super(Object.values(errors).flat()[0] ?? UNKNOWN_ERROR)
    this.status = status
    this.errors = errors
  }
}

// The `{field: [messages]}` shape forms and alerts expect, for API and unexpected errors alike.
export function errorsOf(error) {
  return error?.errors ?? { non_field_errors: [String(error)] }
}

function readCookie(name) {
  const match = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null
}

async function fetchCsrfToken() {
  await fetch('/api/auth/csrf/', { credentials: 'same-origin' })
  return readCookie('csrftoken')
}

async function send(path, { method, body }, csrfToken) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (csrfToken) headers['X-CSRFToken'] = csrfToken

  try {
    return await fetch(`/api${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, { non_field_errors: [NETWORK_ERROR] })
  }
}

export function isCsrfError(status, errors) {
  return status === 403 && String(errors?.detail ?? '').includes('CSRF')
}

export async function request(path, { method = 'GET', body } = {}) {
  const unsafe = UNSAFE_METHODS.has(method)
  // Django rotates the token on login, so always read the current cookie.
  let token = unsafe ? (readCookie('csrftoken') ?? (await fetchCsrfToken())) : null

  let response = await send(path, { method, body }, token)
  let data = response.status === 204 ? null : await response.json().catch(() => null)

  if (unsafe && isCsrfError(response.status, data?.errors)) {
    token = await fetchCsrfToken()
    response = await send(path, { method, body }, token)
    data = response.status === 204 ? null : await response.json().catch(() => null)
  }

  if (!response.ok) {
    throw new ApiError(response.status, data?.errors ?? { non_field_errors: [UNKNOWN_ERROR] })
  }
  return data
}

export const authApi = {
  me: () => request('/auth/me/'),
  register: (payload) => request('/auth/register/', { method: 'POST', body: payload }),
  login: (credentials) => request('/auth/login/', { method: 'POST', body: credentials }),
  logout: () => request('/auth/logout/', { method: 'POST' }),
  updateProfile: (changes) => request('/auth/me/', { method: 'PATCH', body: changes }),
}

export const gamesApi = {
  list: () => request('/games/'),
  create: () => request('/games/', { method: 'POST' }),
  get: (id) => request(`/games/${id}/`),
  join: (id) => request(`/games/${id}/join/`, { method: 'POST' }),
  leave: (id) => request(`/games/${id}/leave/`, { method: 'POST' }),
  start: (id) => request(`/games/${id}/start/`, { method: 'POST' }),
  cancel: (id) => request(`/games/${id}/cancel/`, { method: 'POST' }),
}
