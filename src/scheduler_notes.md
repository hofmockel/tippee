# Scheduling Notes

This system is designed to run once daily. It requires no always-on process or server.

## Cron Setup

To run the daily scan at 9 AM every day:

```bash
0 9 * * * cd /path/to/tippee && python -m src.main run
```

Replace `/path/to/tippee` with your actual repository path.

### Finding Your Path
```bash
# Get the full path to your repository
pwd
# Then use that in the cron command
```

## Manual Execution

Run manually anytime with:

```bash
python -m src.main run
```

## Backfill

Before first production run, perform backfill to populate seen hashes:

```bash
python -m src.main backfill --days 30
```

This marks all current disclosures as seen without sending alerts.

## Verifying Cron

To verify your cron job is scheduled:

```bash
crontab -l
```

To edit and add the job:

```bash
crontab -e
```

## Troubleshooting

- Check `/logs/app.log` for errors
- Ensure FMP API key is valid in `.env`
- Verify Discord webhook is working
- Run `python -m src.main test-alert` to test Discord connectivity

For more details, see [docs/MANUAL.md](../docs/MANUAL.md).