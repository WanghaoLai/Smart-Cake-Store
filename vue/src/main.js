import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { fileUrl } from '@/utils/fileUrl'

import '@/assets/css/global.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
// 模板内直接 $fileUrl(...) 把库里的相对文件路径拼成当前环境的绝对地址
app.config.globalProperties.$fileUrl = fileUrl
app.mount('#app')
