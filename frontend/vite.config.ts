import fs from 'node:fs'
import path from 'node:path'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import { sentryVitePlugin } from '@sentry/vite-plugin'

function firebaseSwPlugin(mode: string) {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    name: 'firebase-sw-from-template',
    buildStart() {
      const tpl = path.resolve(__dirname, 'docker/firebase-messaging-sw.template.js')
      const out = path.resolve(__dirname, 'public/firebase-messaging-sw.js')
      let content = fs.readFileSync(tpl, 'utf-8')
      content = content.replace(/\$\{(\w+)}/g, (_, key) => env[key] ?? '')
      fs.writeFileSync(out, content, 'utf-8')
      console.log('[fcm-sw] Service worker written from template')
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN
  const sentryOrg = process.env.SENTRY_ORG
  const sentryProject = process.env.SENTRY_PROJECT
  const shouldEnableSentryPlugin =
    mode === 'production' && !!sentryAuthToken && !!sentryOrg && !!sentryProject

  return {
    plugins: [
      firebaseSwPlugin(mode),
      react(),
      visualizer({
        filename: 'dist/stats.html',
        open: false,
        gzipSize: true,
        brotliSize: true,
      }),
      ...(shouldEnableSentryPlugin
        ? [
            sentryVitePlugin({
              org: sentryOrg,
              project: sentryProject,
              authToken: sentryAuthToken,
              sourcemaps: {
                filesToDeleteAfterUpload: ['dist/**/*.map'],
              },
            }),
          ]
        : []),
    ],
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    },
    server: {
      port: 5173,
      headers: {
        'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
      },
      proxy: {
        '/api/v1': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'http://127.0.0.1:8081',
          changeOrigin: true,
          ws: true,
          rewriteWsOrigin: true,
        },
        '/presence': {
          target: 'http://127.0.0.1:8081',
          changeOrigin: true,
        },
      },
    },
    build: {
      sourcemap: true,
      // Main bundle ~660kB minified (maps + deps); acceptable until route-based code-splitting
      chunkSizeWarningLimit: 700,
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            query: ['@tanstack/react-query'],
            firebase: ['firebase/app', 'firebase/auth', 'firebase/messaging'],
            sentry: ['@sentry/react'],
            i18n: ['i18next', 'react-i18next', 'i18next-browser-languagedetector', 'i18next-http-backend', 'i18next-icu'],
            forms: ['react-hook-form', 'zod', '@hookform/resolvers'],
            charts: ['recharts'],
          },
        },
      },
    },
  }
})
