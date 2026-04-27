# Scheduling Notes

This system is designed to run once daily. It requires no always-on process or server.

## GitHub Actions Schedule (Recommended)

The repository includes `.github/workflows/main.yml` for automated daily runs on GitHub.

- Workflow trigger: `schedule`
- Current cron: `27 13 * * 1-5` (UTC weekdays)
- Local time equivalent:
  - **Eastern Daylight Time (EDT): 9:27 AM**
  - **Eastern Standard Time (EST): 8:27 AM**

Why `:27` instead of `:00`? GitHub warns that scheduled workflows can be delayed or occasionally dropped during periods of high load, especially at the top of the hour.

If a schedule appears not to run:
- Confirm the workflow file exists on the **default branch**.
- Confirm Actions are enabled for the repository.
- Confirm the repository has had recent activity (public repos can have schedules auto-disabled after long inactivity).
- Use `workflow_dispatch` to run once manually and verify secrets/config.

## Cron Setup

To run the daily scan 3 minutes before U.S. market open (9:27 AM Eastern on weekdays):

```bash
CRON_TZ=America/New_York
27 9 * * 1-5 cd /path/to/tippee && python -m src.main run
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
python -m src.main backfill
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
