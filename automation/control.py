from __future__ import annotations

import argparse

from automation.common import CONFIG_PATH, STATE_PATH, atomic_write_json, iso_z, load_json
from automation.dashboard_state import build_public_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a safe control-plane change.")
    parser.add_argument("action", choices=[
        "pause", "resume", "refresh",
        "creator_pause", "creator_resume", "publishing_pause", "publishing_resume",
    ])
    args = parser.parse_args()
    config = load_json(CONFIG_PATH)
    state = load_json(STATE_PATH)
    if args.action == "pause":
        config["automation"]["enabled"] = False
        config["automation"]["creator_enabled"] = False
        config["automation"]["publishing_enabled"] = False
        message = "Creator and publishing paused"
    elif args.action == "resume":
        config["automation"]["enabled"] = True
        config["automation"]["creator_enabled"] = True
        config["automation"]["publishing_enabled"] = True
        message = "Creator and publishing resumed"
    elif args.action == "creator_pause":
        config["automation"]["creator_enabled"] = False
        message = "Autonomous creator paused"
    elif args.action == "creator_resume":
        config["automation"]["creator_enabled"] = True
        message = "Autonomous creator resumed"
    elif args.action == "publishing_pause":
        config["automation"]["publishing_enabled"] = False
        config["automation"]["enabled"] = False
        message = "Publishing paused; creation can continue"
    elif args.action == "publishing_resume":
        config["automation"]["publishing_enabled"] = True
        config["automation"]["enabled"] = True
        message = "Publishing resumed"
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
