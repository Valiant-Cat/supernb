#!/usr/bin/env python3

import json
import os
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: ensure-opencode-plugin.py <config-path> <plugin-entry>", file=sys.stderr)
        return 1

    config_path = sys.argv[1]
    plugin_entry = sys.argv[2]

    config = {}
    if os.path.exists(config_path):
      with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    if not isinstance(config, dict):
        raise SystemExit(f"Expected a JSON object in {config_path}")

    plugins = config.get("plugin", [])
    if isinstance(plugins, str):
        plugins = [plugins]
    elif plugins is None:
        plugins = []
    elif not isinstance(plugins, list):
        raise SystemExit(f"Expected 'plugin' to be a string or list in {config_path}")

    if plugin_entry not in plugins:
        plugins.append(plugin_entry)

    config["plugin"] = plugins

    os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
