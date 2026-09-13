// Retain intent IDs across ambiguous network failures and page reloads.
export function createPurchaseClient({ post, storage, owner, randomId }) {
  const pending = new Map()
  return function submit(endpoint, payload) {
    const key = 'purchase:' + JSON.stringify([owner(), endpoint, payload])
    if (pending.has(key)) return pending.get(key)
    const request_id = storage.getItem(key) || randomId()
    storage.setItem(key, request_id)
    const task = Promise.resolve().then(() => post(endpoint, { ...payload, request_id }))
      .then(result => {
        if (result.code === '200') storage.removeItem(key)
        return result
      }).finally(() => pending.delete(key))
    pending.set(key, task)
    return task
  }
}
export function parseSpecs(value) {
  return (value || '').split(/[/／|、；,，\s]+/).filter(Boolean)
}
