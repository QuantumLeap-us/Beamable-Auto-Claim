# Beamable Auto Claim

[Click to Register](https://hub.beamable.network/ref/C5SXY97H) Beamable Network

This is an automated script that performs claim operations based on the countdown displayed on the Beamable Network website.

## Features

- Automatically performs claim operations based on the countdown displayed on the website
- Uses HTTP requests to get countdown information, no browser needed
- Uses UTC time for all time calculations, consistent with Beamable Network
- Defaults to a 12-hour interval if countdown cannot be parsed
- Supports custom Cookie configuration
- Detailed logging
- Performs a claim operation immediately upon startup
- Intelligently adjusts the next claim time
- Ensures claims are performed before UTC 00:00 each day

## Installation

1. Ensure Python 3.7 or higher is installed
2. Clone or download this repository
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the environment variables example file and configure it:

```bash
cp .env.example .env
```

5. Edit the `.env` file, replacing `BEAMABLE_COOKIE` with your actual Cookie value

## Usage

Run the following command to start the Auto Claim program:

```bash
python auto_claim.py
```

Alternatively, on Windows, you can simply double-click the `start.bat` file.

The program will immediately perform a claim operation and automatically schedule the next claim based on the countdown displayed on the website.

## How to Get Your Cookie

1. Log in to the Beamable Network website (https://hub.beamable.network)
2. Open browser developer tools (F12 or right-click -> Inspect)
3. Switch to the "Network" tab
4. Refresh the page
5. Find any request and look at its "Request Headers"
6. Find the "Cookie" field and copy its value
7. Paste the copied value into the `.env` file for the `BEAMABLE_COOKIE` variable

## Logging

Program logs are saved in the `auto_claim.log` file and also displayed in the console. All log timestamps are shown in UTC time, formatted as `YYYY-MM-DD HH:MM:SS UTC`.

## How It Works

1. The program performs a claim operation immediately upon startup
2. The program uses HTTP requests to get the webpage content and parse the countdown information
3. The program schedules the next claim based on the parsed countdown
4. If the countdown cannot be parsed, it uses the default 12-hour interval
5. After each successful claim, it gets and sets the time for the next claim
6. All time calculations use UTC time, consistent with the Beamable Network website
7. The program ensures claims are performed before UTC 00:00 each day (actually at 23:30 UTC to provide a 30-minute buffer)

## About Timezones

The Beamable Network website displays countdowns in UTC time. This script also uses UTC time for all time calculations to ensure synchronization with the website. This means:

- Times displayed in logs are in UTC time, which may differ from your local time
- The script gets the actual countdown directly from the webpage, ensuring accuracy
- The script automatically handles timezone differences, ensuring claim operations are performed at the correct time

## Notes

- Cookies may expire; if claim operations fail, update the Cookie value
- It is recommended to deploy this program on a server that runs 24/7
- The default claim interval is 12 hours; to change this, modify the `schedule_default_claim` function in the `auto_claim.py` file 