import { test } from 'node:test'
import assert from 'node:assert/strict'
import { goodsPayload } from '../src/utils/goodsPayload.mjs'
test('editing a listed product only sends writable fields and keeps shelf life', () => {
 const form = goodsPayload({id:1,name:'蛋糕',price:'60',num:4,categoryName:'分类',categoryId:2,shelf_life:'24小时',salesCount:8})
 assert.deepEqual(form,{id:1,name:'蛋糕',price:'60',num:4,shelfLife:'24小时',categoryId:2})
 form.shelfLife='48小时'
 assert.equal(goodsPayload(form).shelfLife,'48小时')
})
