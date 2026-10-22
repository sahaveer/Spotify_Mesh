module.exports = {
  apps: [
    {
      name: "media-player",
      script: "run_server.py",
      interpreter: process.platform === "win32" ? "python" : "venv/bin/python3",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      max_memory_restart: "400M",
      env: {
        PORT: 8000
      }
    }
  ]
};
