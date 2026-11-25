import json
import subprocess
import sys


def handle_post_tool_use(payload: dict) -> int:
    tool_resp = payload.get("tool_response")
    if tool_resp is None:
        return 0

    is_error_flag = isinstance(tool_resp, dict) and tool_resp.get("isError") is True
    raw_text = (
        json.dumps(tool_resp, ensure_ascii=False)
        if not isinstance(tool_resp, str)
        else tool_resp
    )
    lower = raw_text.lower()

    hard_stop_triggers = (
        "401 unauthorized",
        "403 forbidden",
        '"error_class": "forbidden"',
        '"error_class":"forbidden"',
        "token expired",
        "authentication failed",
        "layer 1 law violation",
        "inhibitor_circuit_breaker",
    )
    matched = [t for t in hard_stop_triggers if t in lower]
    if is_error_flag or matched:
        reason = matched[0] if matched else "tool returned isError=true"
        out = {
            "continue": False,
            "stopReason": f"cicada Hard-Stop ({reason}): {raw_text[:280].strip()}",
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def handle_pre_tool_use(payload: dict) -> int:
    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("command") or tool_input.get("file_path") or ""
    res = subprocess.run(
        [
            "living_automaton_kernel.exe",
            "--profile",
            "agent-guard",
            "--data-dir",
            ".lak-data",
            "--workspace",
            ".",
            "--cmd",
            f"pulse proc {target}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (res.stdout or "") + (res.stderr or "")
    if any(
        k in out
        for k in (
            "BLOCKED",
            "Layer 1",
            "Layer 2",
            "INHIBITOR_CIRCUIT_BREAKER",
            "ERROR",
        )
    ):
        sys.stderr.write(f"Blocked by Agent-Guard Kernel: {out.strip()}\n")
        return 2
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    event_name = payload.get("hook_event_name", "")
    if event_name == "PostToolUse" or "tool_response" in payload:
        return handle_post_tool_use(payload)
    return handle_pre_tool_use(payload)


if __name__ == "__main__":
    sys.exit(main())

