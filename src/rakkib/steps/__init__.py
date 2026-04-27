"""Rakkib setup steps.

Each step module exports ``run()`` and ``verify()``:
- ``run()`` executes the step idempotently.
- ``verify()`` returns ok or a structured failure (step, log path, state slice).

Planned modules:
- prereqs.py       # step 00
- layout.py        # step 10
- caddy.py         # step 30
- cloudflare.py    # step 40
- postgres.py      # step 50
- services.py      # step 60
- cron.py          # step 80
- verify.py        # step 90
"""
