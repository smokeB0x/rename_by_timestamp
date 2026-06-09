# rename_by_timestamp
Script that takes the timestamp in filename, calculates the date/time, and renames the files with the date/time

# Basic (uses local system timezone)
python rename_by_timestamp.py /path/to/folder

# With a specific timezone (important for forensic accuracy)
python rename_by_timestamp.py /path/to/folder --timezone UTC
python rename_by_timestamp.py /path/to/folder --timezone Europe/Oslo

# Preview without touching files
python rename_by_timestamp.py /path/to/folder --dry-run

# Custom log path
python rename_by_timestamp.py /path/to/folder --log C:\Logs\rename_log.txt
