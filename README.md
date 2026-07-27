# Million Dollars App

An installable dashboard for channel stats.

**This repository contains no channel IDs and no API key.** Configuration reaches a
device once, through a setup link, and lives only in that browser's localStorage.

`channels.enc` and `status.json` are refreshed every 30 minutes by a scheduled
workflow that reads the channel list from an encrypted repository secret. The list is
published AES-GCM encrypted and the statuses are keyed by SHA-256, so no identifier is
ever committed here.

## Editing the app
Edit the single source file:

    C:\Users\Zahid\YT-Dashboard\dashboard.html

then run `python build.py` and push. Phone and desktop both load the published build,
so one push updates every device.
