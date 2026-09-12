// Only writable fields cross the boundary; display and relation fields stay local.
export function goodsPayload(form) {
  const fields = ['id','name','price','num','description','detail','ingredients','specs',
    'shelfLife','weight','origin','serves','img','unit','categoryId']
  const normalized = { ...form, shelfLife: form.shelfLife ?? form.shelf_life,
    categoryId: form.categoryId ?? form.category_id }
  return Object.fromEntries(fields.filter(k => normalized[k] !== undefined).map(k => [k, normalized[k]]))
}
