const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

function commandExists(command, args = ["--version"]) {
  try {
    const isWindows = process.platform === "win32";
    const commandLine = [command, ...args].join(" ");
    const result = spawnSync(command, args, {
      cwd: root,
      encoding: "utf8",
      shell: false,
      timeout: 5000,
    });
    const output = `${result.stdout || ""}${result.stderr || ""}`.trim();
    if (!isWindows || result.status === 0) {
      return { ok: result.status === 0, output };
    }

    const shellResult = spawnSync(commandLine, {
      cwd: root,
      encoding: "utf8",
      shell: true,
      timeout: 5000,
    });
    const shellOutput = `${shellResult.stdout || ""}${shellResult.stderr || ""}`.trim();
    return {
      ok: shellResult.status === 0,
      output: shellOutput || output,
    };
  } catch (error) {
    return {
      ok: false,
      output: error instanceof Error ? error.message : String(error),
    };
  }
}

function checkPort(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: "127.0.0.1", port });
    socket.setTimeout(1500);
    socket.on("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.on("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.on("error", () => resolve(false));
  });
}

async function checkHttp(url) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 2500);
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timer);
    return { ok: response.ok, status: response.status };
  } catch {
    return { ok: false, status: null };
  }
}

function line(status, label, detail = "") {
  const normalized = status === true ? "ok" : status === false ? "fail" : status;
  const marker = normalized === "ok" ? "OK" : normalized === "warn" ? "WARN" : "FAIL";
  console.log(`${marker.padEnd(4)} ${label}${detail ? ` - ${detail}` : ""}`);
}

async function main() {
  console.log("FoldForge doctor\n");

  const node = commandExists("node");
  line(node.ok, "Node.js", node.output.split(/\r?\n/)[0] || "not found");

  const npm = commandExists("npm.cmd");
  line(npm.ok, "npm.cmd", npm.output.split(/\r?\n/)[0] || "not found");

  const webNodeModules = fs.existsSync(path.join(root, "apps", "web", "node_modules"));
  line(webNodeModules ? "ok" : "fail", "Web dependencies", webNodeModules ? "installed" : "run npm install --prefix apps/web");

  const python = commandExists("python", ["--version"]);
  const py = commandExists("py", ["--version"]);
  if (python.ok) {
    line("ok", "Python", python.output);
  } else if (py.ok) {
    line("ok", "Python launcher", py.output);
  } else {
    line("fail", "Python", "not usable; install Python 3.11+ before running apps/api");
  }

  const apiVenvCfg = path.join(root, "apps", "api", ".venv", "pyvenv.cfg");
  if (fs.existsSync(apiVenvCfg)) {
    const cfg = fs.readFileSync(apiVenvCfg, "utf8");
    const brokenInkscapeVenv = cfg.includes("Inkscape");
    line(
      brokenInkscapeVenv ? "warn" : "ok",
      "API virtualenv",
      brokenInkscapeVenv
        ? "points to Inkscape Python; recreate with Python 3.11+"
        : "present",
    );
  } else {
    line("warn", "API virtualenv", "missing; create apps/api/.venv");
  }

  const docker = commandExists("docker");
  line(docker.ok ? "ok" : "warn", "Docker", docker.ok ? docker.output.split(/\r?\n/)[0] : "not found");

  const webPort = await checkPort(3000);
  line(webPort ? "ok" : "warn", "Port 3000", webPort ? "frontend is listening" : "frontend is not running");

  const apiPort = await checkPort(8000);
  line(apiPort ? "ok" : "warn", "Port 8000", apiPort ? "API is listening" : "API is not running");

  const home = await checkHttp("http://localhost:3000/");
  line(home.ok ? "ok" : "warn", "Frontend homepage", home.status ? `HTTP ${home.status}` : "not reachable");

  const health = await checkHttp("http://localhost:8000/health");
  line(health.ok ? "ok" : "warn", "API health", health.status ? `HTTP ${health.status}` : "not reachable");

  const gitStatus = commandExists("git", ["status", "--short"]);
  if (gitStatus.ok && gitStatus.output) {
    const changed = gitStatus.output.split(/\r?\n/).length;
    line("warn", "Git worktree", `${changed} changed file(s)`);
  } else if (gitStatus.ok) {
    line("ok", "Git worktree", "clean");
  }

  console.log("\nRequired for full release validation: frontend build + API pytest + upload/process/export E2E.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
