import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: { port: 3193 },
  test: { environment: 'jsdom' },
  // Vitest 在 Node 里跑，但组件要按浏览器入口解析，否则会拿到 svelte 服务端构建
  resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
})
