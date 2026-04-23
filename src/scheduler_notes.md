# Scheduling Notes

This system is designed to run once daily.

## Cron Setup

To run the daily scan at 9 AM every day:

```
0 9 * * * cd /path/to/congress-trade-watcher && python -m src.main run
```

Replace `/path/to/congress-trade-watcher` with the actual path.

## Manual Execution

Run manually with:

```
python -m src.main run
```

## Backfill

Before first production run, perform backfill:

```
python -m src.main backfill --days 30
```

This populates seen_hashes without sending alerts.