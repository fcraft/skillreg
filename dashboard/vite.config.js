import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

function autoStartServer() {
  let childProc = null
  const SERVER_DIR = new URL('../server', import.meta.url).pathname
  const DEFAULT_PORT = 3001

  function getServerUrl(port) {
    return `http://localhost:${port}`
  }

  function spawnServer() {
    return import('node:child_process').then(({ spawn }) => {
      const proc = spawn('node', ['index.js'], {
        cwd: SERVER_DIR,
        stdio: 'inherit',
        env: { ...process.env, PORT: String(DEFAULT_PORT), SERVER_IDLE_SHUTDOWN: 'false' },
      })
      proc.on('exit', (code) => {
        console.log(`[auto-start] Server exited with code ${code}`)
        if (childProc === proc) childProc = null
      })
      childProc = proc
      return proc
    })
  }

  function killServer() {
    if (childProc && !childProc.killed) {
      console.log('[auto-start] Stopping server...')
      childProc.kill('SIGTERM')
      childProc = null
    }
  }

  async function waitForHealth(port, timeoutMs = 15_000) {
    const deadline = Date.now() + timeoutMs
    while (Date.now() < deadline) {
      try {
        const res = await fetch(`http://localhost:${port}/api/health`)
        if (res.ok) return true
      } catch {
        // not ready yet
      }
      await new Promise(r => setTimeout(r, 500))
    }
    return false
  }

  async function discoverServerPort(startPort = DEFAULT_PORT) {
    for (let p = startPort; p < startPort + 50; p++) {
      try {
        const res = await fetch(`http://localhost:${p}/api/health`)
        if (res.ok) {
          const health = await res.json()
          return health.port || p
        }
      } catch {}
    }
    return null
  }

  return {
    name: 'auto-start-server',
    configureServer(server) {
      // Auto-start on first listen
      server.httpServer?.once('listening', async () => {
        let actualPort = await discoverServerPort()

        if (!actualPort) {
          console.log('[auto-start] Starting agent-hub server...')
          await spawnServer()
          const ok = await waitForHealth(DEFAULT_PORT)
          if (ok) actualPort = await discoverServerPort() || DEFAULT_PORT
        }

        if (actualPort) {
          server.config.server.proxy['/api'].target = getServerUrl(actualPort)
        }
      })

      // Restart endpoint
      server.middlewares.use('/dev/restart-server', async (_req, res) => {
        res.setHeader('Content-Type', 'application/json')
        try {
          killServer()
          await new Promise(r => setTimeout(r, 500))
          await spawnServer()
          const ok = await waitForHealth(DEFAULT_PORT)
          if (ok) {
            const port = await discoverServerPort() || DEFAULT_PORT
            server.config.server.proxy['/api'].target = getServerUrl(port)
            res.statusCode = 200
            res.end(JSON.stringify({ success: true, port }))
          } else {
            res.statusCode = 500
            res.end(JSON.stringify({ error: 'Server did not become healthy in time' }))
          }
        } catch (err) {
          res.statusCode = 500
          res.end(JSON.stringify({ error: err.message }))
        }
      })

      // Kill server when Vite shuts down
      server.httpServer?.on('close', () => {
        killServer()
      })
    },
  }
}

export default defineConfig({
  plugins: [vue(), autoStartServer()],
  server: {
    port: 17880,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
})
