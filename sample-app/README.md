# northgate platform-worker

Internal job worker for Northgate Financial. Processes three job kinds
from the queue spool: tenant config reloads, settlement notifications,
avatar thumbnails, and support-console query lookups.

**This repo is a demo fixture for the Reach triage copilot.** Its
dependency pins are deliberately stale (they mirror a typical
mid-2020s internal service), which is exactly what a vulnerability
scanner sees in production estates.

Do not deploy. Do not install these versions anywhere.

## Run (fixture only)

```bash
python3 -m app.main
```
