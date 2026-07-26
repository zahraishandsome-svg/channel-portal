# Channel portal

An installable dashboard for YouTube channel stats.

**This repository contains no channel IDs and no API key.** Configuration is supplied
once per device through a setup link and lives only in that browser's localStorage.

`status.json` is refreshed every 30 minutes by a scheduled workflow that reads the
channel list from an encrypted repository secret (`CHANNEL_IDS`) and writes results
keyed by SHA-256, so no identifier is ever published here.
