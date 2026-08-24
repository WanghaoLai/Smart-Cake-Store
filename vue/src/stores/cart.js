import { defineStore } from 'pinia'
import request from '@/utils/request'

// 购物车全局状态：角标数量与列表由同一 store 派生，
// 任意组件增删改后调用 refreshCount/刷新列表即可全站同步。
export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [],        // 购物车条目（含商品实时信息）
    count: 0,         // 角标：商品总件数
    loaded: false,    // 列表是否已加载（购物车页进入时懒加载）
  }),

  getters: {
    selectedItems: (s) => s.items.filter(i => i.selected),
    selectedCount: (s) => s.items.filter(i => i.selected).reduce((sum, i) => sum + i.num, 0),
    selectedTotal: (s) => s.items
      .filter(i => i.selected)
      .reduce((sum, i) => sum + Number(i.goodsPrice) * i.num, 0),
    allSelected: (s) => s.items.length > 0 && s.items.every(i => i.selected),
  },

  actions: {
    async loadCount() {
      try {
        const res = await request.get('/cart/count')
        if (res.code === '200') this.count = res.data?.count || 0
      } catch { /* 角标失败静默，不打扰用户 */ }
    },

    async loadCart() {
      const res = await request.get('/cart/list')
      if (res.code === '200') {
        this.items = res.data?.list || []
        this.count = this.items.reduce((sum, i) => sum + i.num, 0)
        this.loaded = true
      }
      return this.items
    },

    async addGoods(goodsId, num = 1) {
      const res = await request.post('/cart/add', { goodsId, num })
      if (res.code === '200') this.loadCount()
      return res
    },

    async updateNum(item) {
      const res = await request.put(`/cart/update/${item.id}`, { num: item.num })
      if (res.code === '200') this.loadCount()
      return res
    },

    async removeOne(id) {
      const res = await request.delete(`/cart/remove/${id}`)
      if (res.code === '200') {
        this.items = this.items.filter(i => i.id !== id)
        this.loadCount()
      }
      return res
    },

    async removeBatch(ids) {
      const res = await request.post('/cart/remove-batch', { ids })
      if (res.code === '200') {
        this.items = this.items.filter(i => !ids.includes(i.id))
        this.loadCount()
      }
      return res
    },

    async toggleSelect(item) {
      await request.put(`/cart/select/${item.id}`, { selected: item.selected })
    },

    async toggleSelectAll(selected) {
      const res = await request.put('/cart/select-all', { selected })
      if (res.code === '200') this.items.forEach(i => { i.selected = selected })
      return res
    },

    async checkout(ids, addressId) {
      const res = await request.post('/cart/checkout', { ids, addressId })
      if (res.code === '200') {
        this.items = this.items.filter(i => !ids.includes(i.id))
        this.loadCount()
      }
      return res
    },
  },
})
