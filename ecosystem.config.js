// pm2 config: runs the MCP server and the ngrok tunnel, restarts both if they die.
//   pm2 start ecosystem.config.js
//   pm2 save            (remember the process list)
//   pm2 startup         (Linux/macOS: prints a command to run so pm2 starts on boot)
const fs = require("fs");
const path = require("path");

// tiny .env reader so the ngrok app gets PUBLIC_HOST and PORT
const env = {};
try {
  for (const line of fs.readFileSync(path.join(__dirname, ".env"), "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/);
    if (m && !line.trim().startsWith("#")) env[m[1]] = m[2];
  }
} catch (e) {
  console.error("No .env found. Copy .env.example to .env first.");
}

const python =
  process.platform === "win32"
    ? path.join(__dirname, ".venv", "Scripts", "python.exe")
    : path.join(__dirname, ".venv", "bin", "python");

module.exports = {
  apps: [
    {
      name: "mcp-server",
      script: "server.py",
      interpreter: python,
      cwd: __dirname,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },
    {
      name: "mcp-tunnel",
      script: "ngrok",
      args: `http --url=${env.PUBLIC_HOST || "YOUR-DOMAIN.ngrok-free.dev"} ${env.PORT || 8000}`,
      interpreter: "none",
      autorestart: true,
      restart_delay: 3000,
    },
  ],
};
