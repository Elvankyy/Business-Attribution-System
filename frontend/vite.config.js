import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // 与后端共用项目根目录的 .env，Vite 只暴露 VITE_ 前缀变量。
  envDir: fileURLToPath(new URL('..', import.meta.url)),
  server: {
    port: 5173,
    strictPort: true,
  },
})
