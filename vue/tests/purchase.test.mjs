import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createPurchaseClient } from '../src/utils/purchase.mjs'

test('double click and network retry keep one request ID, success allows new purchase', async () => {
  const values = new Map(), calls = []
  const storage = { getItem: k => values.get(k), setItem: (k,v) => values.set(k,v), removeItem: k => values.delete(k) }
  let fail = true, id = 0
  const submit = createPurchaseClient({ storage, owner: () => ['用户',7], randomId: () => 'intent_' + ++id,
    post: async (url,payload) => { calls.push(payload); if (fail) throw Error('timeout'); return {code:'200'} } })
  const a = submit('/orders/add',{goodsId:1}), b = submit('/orders/add',{goodsId:1})
  assert.equal(a,b)
  await assert.rejects(a)
  fail = false
  await submit('/orders/add',{goodsId:1})
  assert.equal(calls[0].request_id,calls[1].request_id)
  await submit('/orders/add',{goodsId:1})
  assert.notEqual(calls[1].request_id,calls[2].request_id)
})
