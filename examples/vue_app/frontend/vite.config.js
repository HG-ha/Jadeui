import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',  // 重要：使用相对路径
  build: {
    outDir: '../web',  // 输出到 web 目录
    emptyOutDir: true,
  },
})

