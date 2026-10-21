from __future__ import annotations

import argparse

from automation.common import CONFIG_PATH, STATE_PATH, atomic_write_json, iso_z, load_json
from automation.dashboard_state import build_public_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a safe control-plane change.")
    parser.add_argument("action", choices=["pause", "resume", "refresh"])
    args = parser.parse_args()
    config = load_json(CONFIG_PATH)
    state = load_json(STATE_PATH)
    if args.action == "pause":
        config["automation"]["enabled"] = False
        message = "Automation paused"
    elif args.action == "resume":
        config["automation"]["enabled"] = True
        message = "Automation resumed"
    else:
        message = "Dashboard state refreshed"
    atomic_write_json(CONFIG_PATH, config)
    events = state.setdefault("events", [])
    events.insert(0, {"at": iso_z(), "level": "info", "message": message})
    del events[30:]
    atomic_write_json(STATE_PATH, state)
    atomic_write_json(STATE_PATH, build_public_state())
    print(message)


if __name__ == "__main__":
    main()
