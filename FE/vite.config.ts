import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

// SPA: /onboarding/step1 등 직접 접근 시 index.html 제공 (개발 서버 404 방지)
function spaFallback() {
  return {
    name: "spa-fallback",
    configureServer(server: import("vite").ViteDevServer) {
      const fn = (req: { url?: string; method?: string }, _res: unknown, next: () => void) => {
        const url = req.url ?? ""
        if (
          req.method === "GET" &&
          !url.includes(".") &&
          !url.startsWith("/@") &&
          !url.startsWith("/node_modules") &&
          url !== "/"
        ) {
          req.url = "/index.html"
        }
        next()
      }
      const stack = server.middlewares.stack as Array<{ route: string; handle: unknown }>
      stack.unshift({ route: "", handle: fn })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), spaFallback()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
