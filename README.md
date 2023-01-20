# Operation Planner

Example code of generating satellite pass event information using the PyEphem library and exporting to the Google Calendar API.
This example was written and tested on the Ubuntu 22.04 GNU/Linux distribution.

## Setup

1) Configure the environment and generate a valid credentials file. This can be accomplished by following the steps from: https://developers.google.com/calendar/api/quickstart/python
2) Create one or more google calendars and adjust the calendar ID entries in the operation_planner.py file.
3) Adjust the satellite name and TLE download script (download_tle.sh)

Execution of the program can be done as:

```
python ./operation_planner/main.py
```

## License

This software is licensed under Apache License, Version 2.0
