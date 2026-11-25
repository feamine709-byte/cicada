# Cicada (v0.4.0)

**Local Execution Firewall, Universal MCP Proxy, and Cryptographic Flight Recorder for AI Coding Agents**

Cicada is a standalone, 100% offline execution guard for autonomous coding assistants including Claude Code, Claude Desktop, Cursor, Windsurf, and Antigravity. Built in pure `std` Safe Rust with zero external dependencies, it confines agent file access and command execution to your workspace, strips secrets before they reach the model context, breaks infinite retry loops, and records every event in a tamper-evident SHA-256 audit chain.

---

## Binary Footprint and Runtime Profile

| Property | Specification |
| :--- | :--- |
| **Windows x64 Binary (`living_automaton_kernel.exe`)** | `791.5 KB` (`810,496` bytes) |
| **Linux x64 Binary (`living_automaton_kernel`)** | `921 KB` (`942,328` bytes) |
| **macOS ARM64 / x64 Binaries** | `784 KB` (`802,576` bytes) / `858 KB` (`878,672` bytes) |
| **Language & Safety** | Pure `std` Safe Rust (`#![forbid(unsafe_code)]`) |
| **External Dependencies** | Zero (no Docker, no Python runtime, no Node.js daemon, no cloud APIs) |
| **Network Telemetry** | Zero outbound network calls; zero extra LLM inference overhead |

---

## Key Capabilities

1. **Deterministic Workspace Boundary & Allowlist Enforcement (`--profile agent-guard`)**
   - Blocks destructive commands (`rm -rf`, `del /f`, `format`, `shutdown`), interactive shells (`cmd`, `powershell`, `pwsh`, `bash`, `sh`, `wsl`), command chaining (`&&`, `||`, `|`, `;`, `>`, `<`), parent directory traversal (`..`), absolute system path escapes, NUL-byte smuggling, and symlink / NTFS junction escapes outside `--workspace`.
   - Enforces a strict default binary allowlist (`cargo`, `rustc`, `python`, `git`, `node`, `npm`, `pytest`, extendable via `--allow-bin`) and kills hung child processes after 30 seconds (`--cmd-timeout`).
2. **Inherited Environment Isolation (`.env_clear()`) & Automatic DLP (`[REDACTED]`)**
   - Spawns all child commands and proxied MCP servers with `.env_clear()`, passing only minimal OS baseline variables (`PATH`, `SYSTEMROOT`, `COMSPEC`, `TEMP`, `TMP`, `HOME`, `USERPROFILE`, `LANG`).
   - Scrubs API keys, cloud tokens, and `.env` secrets (`sk-`, `sk_live_`, `ghp_`, `github_pat_`, `AKIA`, `AIza`, and configured `LAK_API_KEY` / `--api-key` tokens) to `[REDACTED]` across file reads, `stdout`/`stderr`, proxied MCP responses, and `audit.log`.
3. **3-Strike Anti-Loop Circuit Breaker (`INHIBITOR_CIRCUIT_BREAKER`)**
   - Tracks consecutive identical failures on commands and proxied MCP tool calls. On the third consecutive failure (`3/3`) without an intervening workspace file modification, `INHIBITOR_CIRCUIT_BREAKER` blocks further identical retries to prevent hallucination loops and token burn.
4. **Silent `401`/`403` Auth-Drop Normalization (`--mcp-proxy`)**
   - Detects disguised `401 Unauthorized`, `403 Forbidden`, `token expired`, and `authentication failed` payloads returned by downstream MCP servers without `isError: true`, normalizing them into structured MCP errors (`"isError": true`, `"error_class": "forbidden"`, `"hard_stop": true`).
5. **Dynamic MCP Tool Pruning (`--prune-tools [K]` & `proxy_discover_tools`)**
   - Filters downstream `tools/list` responses down to the top `K` highest-utility tools ranked by live execution outcomes, injecting `proxy_discover_tools` so agents can retrieve pruned tools on demand by intent keyword without paying prompt-token overhead on every turn.
6. **One-Click IDE Setup, Live Telemetry, HTTP Control, and SHA-256 Audit**
   - `--setup` and `--setup --wrap-existing` automatically detect IDE MCP configs, create `.bak` backups, and register or proxy-wrap servers idempotently.
   - `--monitor [--once]` renders live security blocks, DLP redactions, circuit-breaker trips, and token savings.
   - `--serve <addr>` exposes a hardened local HTTP/1.1 & JSON-RPC API (`/status`, `/pulse`, `/approve`, `/reject`, `/audit`, `/exit`) with constant-time `X-API-Key` / `Bearer` authentication.
   - `kernel_audit_verify` validates the entire append-only FIPS 180-4 SHA-256 `audit.log` hash chain.

---

## Installation & Quickstart

### 1. Download & Verify Checksums

Download the archive for your platform from the [GitHub Releases](https://github.com/feamine709-byte/cicada/releases/tag/v0.4.0) page and verify its SHA-256 digest against `SHA256SUMS.txt`:

- **Windows (PowerShell):**
  ```powershell
  (Get-FileHash .\Cicada-v0.4.0-windows-x64.zip -Algorithm SHA256).Hash
  Expand-Archive .\Cicada-v0.4.0-windows-x64.zip -DestinationPath .\cicada
  ```
- **Linux (`x64`):**
  ```bash
  sha256sum -c SHA256SUMS.txt --ignore-missing
  unzip Cicada-v0.4.0-linux-x64.zip -d ./cicada
  chmod +x ./cicada/living_automaton_kernel
  ```
- **macOS (`arm64` / `x64`):**
  ```bash
  shasum -a 256 Cicada-v0.4.0-macos-*.zip
  unzip Cicada-v0.4.0-macos-arm64.zip -d ./cicada
  chmod +x ./cicada/living_automaton_kernel
  ```

### 2. One-Click IDE Integration (`--setup` & `--wrap-existing`)

Automatically configure Cursor, Claude Desktop, Claude Code, or Antigravity IDE (creating `.bak` backups of existing config files):

```bash
# Register Cicada as a standalone guarded MCP server
./living_automaton_kernel --setup --workspace /path/to/your-project --data-dir .lak-data

# Wrap all existing MCP servers in your IDE config behind the Cicada firewall proxy
./living_automaton_kernel --setup --wrap-existing --workspace /path/to/your-project --data-dir .lak-data
```

On Windows, replace `./living_automaton_kernel` with `.\living_automaton_kernel.exe`.

### 3. Manual MCP Configuration (`presets/cicada.mcp.json`)

Copy `presets/cicada.mcp.json` into your client configuration (update `command` to match your OS binary path):

```json
{
  "mcpServers": {
    "living-automaton-agent-guard": {
      "command": "living_automaton_kernel.exe",
      "args": [
        "--profile", "agent-guard",
        "--workspace", ".",
        "--data-dir", ".lak-data",
        "--cmd-timeout", "30",
        "--mcp-stdio"
      ]
    }
  }
}
```

### 4. Claude Code Hook Integration (`presets/cicada-hook.py`)

`presets/cicada-hook.py` provides a two-stage hook for Claude Code:
- **`PreToolUse`:** Evaluates `tool_input.command` or `tool_input.file_path` against `living_automaton_kernel.exe --profile agent-guard`. On any block (`BLOCKED`, `Layer 1`, `Layer 2`, `INHIBITOR_CIRCUIT_BREAKER`, or `ERROR`), writes the reason to `stderr` and exits with **code `2`** to prevent execution.
- **`PostToolUse`:** Inspects `tool_response` for `isError: true`, `401 unauthorized`, `403 forbidden`, `"error_class": "forbidden"`, `token expired`, `authentication failed`, Layer 1 violations, or `inhibitor_circuit_breaker`. When triggered, outputs `{"continue": false, "stopReason": "cicada Hard-Stop (...)"}` to halt retry loops immediately.

### 5. Universal MCP Proxy & Dynamic Tool Pruning (`--mcp-proxy`)

Wrap any downstream stdio MCP server without modifying its code:

```bash
./living_automaton_kernel \
  --profile agent-guard \
  --workspace /path/to/your-project \
  --data-dir .lak-data \
  --mcp-proxy --prune-tools 6 -- npx -y @modelcontextprotocol/server-filesystem /path/to/your-project
```

---

## Built-In MCP Tools (`--mcp-stdio`)

When connected directly via `--mcp-stdio`, Cicada exposes 9 tools over JSON-RPC 2.0:

1. `workspace_read_file`: Read a file inside `--workspace` with automatic `[REDACTED]` DLP scrubbing.
2. `workspace_write_file`: Write UTF-8 content inside `--workspace` (blocks traversal and symlink escapes) and reset the circuit-breaker counter.
3. `workspace_run_command`: Execute an allowlisted binary with `.env_clear()`, `--cmd-timeout`, DLP scrubbing, and 3-strike circuit breaking.
4. `workspace_adaptive_route`: Rank candidate command strategies, execute the top route, fall back on failure/timeout, and update pathway weights.
5. `workspace_recommend_strategy`: Score and rank candidate strategies against persisted execution telemetry without running them, flagging known-failing options.
6. `workspace_inject_skills`: Scan workspace skill/rule files and inject only top-ranked matches for a task with DLP redaction.
7. `workspace_build_repair_loop`: Execute a bounded multi-step write, build/test, and feedback repair loop.
8. `kernel_status`: Inspect runtime status, active shard counts, policy block counters, checksums, and SHA-256 `audit_head`.
9. `kernel_audit_verify`: Verify the full append-only FIPS 180-4 SHA-256 hash chain of `audit.log`.

---

## Verified Benchmarks & Adversarial Stress Test Results

All results below are captured from real execution runs on Cicada `v0.4.0`:

- **Release Test Suite:** `72/72` tests passing (`0` failed) across sandbox confinement, symlink escape rejection, `.env_clear()` isolation, DLP redaction, MCP stdio framing, proxy normalization, dynamic tool pruning, circuit-breaker tripping, and SHA-256 audit tamper detection.

### 1. Destructive Command Blocking
- `workspace_run_command` (`{"binary": "cmd", "args": ["/c", "del /f /q *"]}`):
  ```text
  Encountered error in tool execution: ERROR: Layer 1 Law Violation: unconditionally forbidden destructive operation
  ```
- `workspace_run_command` (`{"binary": "powershell", "args": ["-Command", "Remove-Item -Recurse -Force ."]}`):
  ```text
  Encountered error in tool execution: ERROR: ProcessAdapter: binary `powershell` is not in allowlist
  ```

### 2. File Exfiltration & Sandbox Escape Prevention
- `workspace_read_file` on `C:\Windows\win.ini`:
  ```text
  Encountered error in tool execution: ERROR: Layer 1 Law Violation: path escapes confined sandbox boundary
  ```
- `workspace_write_file` to `..\..\escape_exfil.txt`:
  ```text
  Encountered error in tool execution: ERROR: Layer 1 Law Violation: path escapes confined sandbox boundary
  ```
- `workspace_read_file` on `.env`:
  ```text
  API_KEY=[REDACTED]
  ```

### 3. Hallucination / Retry Loop Circuit Breaking (4 Consecutive `rm -rf /` Calls)
- **Call 1 & Call 2:** Blocked by Layer 1 (`unconditionally forbidden destructive operation`).
- **Call 3 (`3/3`):**
  ```text
  Encountered error in tool execution: ERROR: INHIBITOR_CIRCUIT_BREAKER: command `rm -rf /` blocked on consecutive failure 3/3 without any workspace file modification; modify a file via workspace_write_file or switch strategy via workspace_adaptive_route
  ```
- **Call 4 (`4/3`):** Blocked immediately without execution.
- **Audit Verification (`kernel_audit_verify`):**
  ```text
  AUDIT_VERIFIED_OK entries=28 head_hash=67d867a32484b06e7f1530ac1f9989fa699175f4f938c038357dd67c46796f26
  ```

### 4. Live `--mcp-proxy --prune-tools 2` Stress Test (10-Tool Downstream Server)
- **Tool Pruning:** `10` downstream tools pruned to `2` (`tool_0`, `tool_1`) plus `proxy_discover_tools`.
- **Outbound DLP Redaction:** `tool_0` response `DB_PASS=sk-prod-9988776655` scrubbed to `DB_PASS=[REDACTED]`.
- **Silent `401` Normalization (`tool_1`):**
  ```json
  {
    "content": [{"type": "text", "text": "{\"error_class\":\"forbidden\",\"hard_stop\":true,\"message\":\"HARD_STOP (forbidden — do not retry or attempt workarounds): 401 Unauthorized: token expired\"}"}],
    "structuredContent": {"error_class": "forbidden", "hard_stop": true, "message": "HARD_STOP (forbidden — do not retry or attempt workarounds): 401 Unauthorized: token expired"},
    "isError": true
  }
  ```
- **Proxied Loop Prevention (`tool_2`):** Calls 3 and 4 tripped `INHIBITOR_CIRCUIT_BREAKER` (`3/3` and `4/3`) before reaching the downstream server.
- **Flight Recorder Metrics (`--monitor --once`):**
  ```text
  Audit Log: 18 entries | SHA-256 Chain: VERIFIED_OK
  [REDACTED] Interceptions  : 1
  INHIBITOR_CIRCUIT_BREAKER : 4 trips
  Retries Prevented         : 4
  Context Pruning Saved     : ~256 tokens
  Est. LLM Tokens Saved     : ~2856

  [LATEST 5 AUDIT EVENTS]
  1. mcp_proxy_inhibited tick=7 strikes=3 tool=tool_2
  2. checkpoint reason=mcp_proxy_inhibited crc32=cc906dd6 fnv1a=56a50f6db4832d45
  3. mcp_proxy_inhibited tick=8 strikes=4 tool=tool_2
  4. checkpoint reason=mcp_proxy_inhibited crc32=35ab7a93 fnv1a=81d86798a16a7b82
  5. checkpoint reason=mcp_proxy_eof crc32=35ab7a93 fnv1a=81d86798a16a7b82
  ```

---

## Need Programmable Policy Rules?

Cicada provides out-of-the-box execution isolation, secret redaction, tool pruning, and circuit breaking completely free. If your workflow requires a programmable 28-command local policy engine, live rule hot-reloading, dry-run validation, and 4 domain presets (AI agents, API guards, n8n webhooks, strict sandboxes), check out Joker v0.5.0 ($29 one-time license).

- Showcase and docs: https://github.com/feamine709-byte/joker
- Direct license and binaries ($29 one-time): https://buy.polar.sh/polar_cl_QNGodSf74F49VETHe1vvfYGvsiEDsqTuNax5V0i8ck1

---

## License

See [LICENSE](./LICENSE) for full licensing terms.
