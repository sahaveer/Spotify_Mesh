const fs = require('fs');
const path = require('path');

let interpreter = process.platform === 'win32' ? 'python' : 'python3';
if (process.platform !== 'win32') {
  if (fs.existsSync(path.join(__dirname, 'venv', 'bin', 'python3'))) {
    interpreter = 'venv/bin/python3';
  } else if (fs.existsSync(path.join(__dirname, '.venv', 'bin', 'python3'))) {
    interpreter = '.venv/bin/python3';
  }
}

module.exports = {
  apps: [
    {
      name: "media-player",
      script: "run_server.py",
      interpreter: interpreter,
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
