# rename_by_timestamp
Script that takes the timestamp in filename, calculates the date/time, and renames the files with the date/time

# Basic (uses local system timezone)
python rename_by_timestamp.py /path/to/folder

# With a specific timezone 
python rename_by_timestamp.py /path/to/folder --timezone UTC

python rename_by_timestamp.py /path/to/folder --timezone Europe/Oslo

# Preview without touching files
python rename_by_timestamp.py /path/to/folder --dry-run

# Custom log path
python rename_by_timestamp.py /path/to/folder --log C:\Logs\rename_log.txt

# About
Timestamp detection — uses regex to find a 13-digit (milliseconds) or 10-digit (seconds) epoch anywhere in the filename, not just at the start.

Sanity bounds — only accepts timestamps that fall between 2000 and 2100, so random number sequences don't get misidentified

Collision handling — if two files resolve to the same datetime, they get suffixed _1, _2, etc.

Extension preserved — works on any file type

Files without a detectable timestamp are skipped and noted in the log

Dry-run mode — lets you verify the output before committing any changes

# Dependencies
Standard library only — no pip installs needed (timezone names like Europe/Oslo require Python 3.9+ via zoneinfo, but UTC and fixed offsets like UTC+2 work on any version)
