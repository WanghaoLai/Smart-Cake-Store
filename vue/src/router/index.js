import {createRouter, createWebHistory} from 'vue-router'

const WHITE_LIST = ['/login', '/register']

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    {
      path: '/manager',
      component: () => import('@/views/Manager.vue'),
      redirect: '/manager/home',
      children: [
        { path: 'person', component: () => import('@/views/manager/Person.vue'), meta: { roles: ['用户', '管理员'] }},
        { path: 'password', component: () => import('@/views/manager/Password.vue'), meta: { roles: ['用户', '管理员'], allowForcedPassword: true }},
        { path: 'home', component: () => import('@/views/manager/Home.vue')},
        { path: 'admin', component: () => import('@/views/manager/Admin.vue'), meta: { roles: ['管理员'] }},
        { path: 'user', component: () => import('@/views/manager/User.vue'), meta: { roles: ['管理员'] }},
        { path: 'category', component: () => import('@/views/manager/Category.vue'), meta: { roles: ['管理员'] }},
        { path: 'goods', component: () => import('@/views/manager/Goods.vue'), meta: { roles: ['管理员'] }},
        { path: 'address', component: () => import('@/views/manager/Address.vue'), meta: { roles: ['用户', '管理员'] }},
        { path: 'cake', component: () => import('@/views/manager/Cake.vue'), meta: { roles: ['用户'] }},
        { path: 'cake/:id', component: () => import('@/views/manager/CakeDetail.vue'), props: true, meta: { roles: ['用户'] }},
        { path: 'cart', component: () => import('@/views/manager/Cart.vue'), meta: { roles: ['用户'] }},
        { path: 'orders', component: () => import('@/views/manager/Orders.vue')},
        { path: 'reviews', component: () => import('@/views/manager/Reviews.vue'), meta: { roles: ['管理员'] }},
        { path: 'notice', component: () => import('@/views/manager/Notice.vue')},
        { path: 'chat', component: () => import('@/views/manager/Chat.vue')},
        { path: 'knowledge', component: () => import('@/views/manager/Knowledge.vue'), meta: { roles: ['管理员'] }},
        { path: 'ops', component: () => import('@/views/manager/Ops.vue'), meta: { roles: ['管理员'] }},
        { path: 'favorite', component: () => import('@/views/manager/Favorite.vue'), meta: { roles: ['用户'] }},
      ]
    },
    { path: '/login', component: () => import('@/views/Login.vue')},
    { path: '/register', component: () => import('@/views/Register.vue')},
  ]
})

router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('token')
    if (token) {
        const user = JSON.parse(localStorage.getItem('system-user') || '{}')
        if (user.must_change_password && !to.meta.allowForcedPassword) {
            next('/manager/password?force=1')
            return
        }
        if (to.meta.roles && !to.meta.roles.includes(user.role)) {
            next('/manager/home')
            return
        }
        if (to.path === '/login') {
            next('/manager/home')
        } else {
            next()
        }
    } else {
        if (WHITE_LIST.includes(to.path)) {
            next()
        } else {
            next('/login')
        }
    }
})

export default router
