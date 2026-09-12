import request from './request'
import { createPurchaseClient } from './purchase.mjs'
export const submitPurchase = createPurchaseClient({
  post: (url, payload) => request.post(url, payload), storage: sessionStorage,
  owner: () => {
    const user = JSON.parse(localStorage.getItem('system-user') || '{}')
    return [user.role, user.id]
  },
  randomId: () => crypto.randomUUID(),
})
