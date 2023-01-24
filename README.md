# Operation Planner
![version info](https://img.shields.io/badge/Python-3.9-blue)
![license](https://img.shields.io/github/license/schulz89/operation_planner)

Satellite pass event information generation tool using the PyEphem library and Google Calendar API.

Satellite TLE data is taken from http://celestrak.org/NORAD/elements/stations.txt

## Setup
### Install Requirments
```bash
pip install -r requirements.txt
```

### Settings
Settings are stored in the ```settings.json``` file.
The settings file contains the coordinates of the base station and the information of the satellites to track.

### Google Calendar API
Configure the environment and generate a valid credentials file. This can be accomplished by following the steps from: https://developers.google.com/calendar/api/quickstart/python

```credentials.json``` should be place in the root repo directory.


## Running the Program
To run the program, run the following command from the root repo directory:

```bash
python ./operation_planner/main.py
```

## License

This software is licensed under Apache License, Version 2.0

