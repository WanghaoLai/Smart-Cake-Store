import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// 导入对应包

import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

import ElementPlus from 'unplugin-element-plus/vite'

// https://vitejs.dev/config/
export default defineConfig({
  // marked/dompurify 只被懒加载的 Chat.vue 引用，不在启动依赖图内；
  // 不预构建时 Vite 会在登录后预取全部页面 chunk 时才发现它们，
  // 触发运行期 re-optimize 并推送整页 reload（表现为"登录后自动刷新一次"）。
  optimizeDeps: {
    include: ['marked', 'dompurify'],
  },
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver(
          { importStyle: 'sass' }
      )],
    }),
    Components({
      resolvers: [ElementPlusResolver(
          { importStyle: 'sass' }
      )],
    }),

    // 按需定制主题配置
    ElementPlus({
      useSource: true,
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('@element-plus/icons-vue')) return 'vendor-element-icons'
          if (id.includes('element-plus/es/components/')) {
            const component = id.split('element-plus/es/components/')[1]?.split('/')[0]
            return component ? `element-${component}` : 'vendor-element'
          }
          if (id.includes('element-plus')) return 'vendor-element-core'
          if (id.includes('marked') || id.includes('dompurify')) return 'vendor-markdown'
          if (id.includes('/vue/') || id.includes('vue-router')) return 'vendor-vue'
          if (id.includes('axios')) return 'vendor-http'
          return 'vendor'
        },
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 自动导入定制化样式文件进行样式覆盖
        additionalData: `
          @use "@/assets/css/index.scss" as *;
        `,
      }
    }
  }
})
