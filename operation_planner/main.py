import json
import ephem
import math
import datetime
import time
import os
import urllib.request
from pytz import timezone
from tabulate import tabulate

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

##################################
# Global variables and constants
##################################

TLE_URL = "http://celestrak.org/NORAD/elements/stations.txt"
SCOPES = ['https://www.googleapis.com/auth/calendar']
_commitChanges = True   # Flag to commit events to Google Calendar
_delta_week = 0
_total_duration = 604800 # a week

####################
# Methods
####################

def getSettings(filename: str) -> dict:
    '''
    Gets settings from settings.json.
    '''
    with open(filename) as json_file:
        return json.load(json_file)

def getTLE(satList: dict, saveTLE: bool = False, TLElocalPath: str = "./satTLE.txt") -> dict:
    '''
    Gets TLE data from URL specified in TLE_URL.
    '''
    # Check for recent local version of TLE data
    if os.path.exists(TLElocalPath) and (time.time() - os.path.getmtime(TLElocalPath))<14400:
        print('Using local TLE data...')
        f = open(TLElocalPath, 'r')
        tle_data = f.read()
        f.close()
        tle_data = tle_data.split('\n') 
    else:
        print('Downloading TLE data...')
        # Fetch TLE text file from URL
        tle_data = urllib.request.urlopen(TLE_URL).read().decode()
        # Save TLE data to file if specified
        if saveTLE:
            with open(TLElocalPath, 'w') as f:
                f.write(tle_data)
        tle_data = tle_data.split('\r\n')   # Split text file by line endings
    # Get TLE data for specified satellites only
    for i in range(0, len(tle_data), 3):
        if tle_data[i].rstrip() in satList.keys():
            satList[tle_data[i].rstrip()]['TLE'] = [tle_data[i+1].rstrip(), tle_data[i+2].rstrip()]
    return satList

def makeObserver(baseInfo: dict) -> ephem.Observer:
    '''
    Makes a pyephem Observer for the ground station given in settings.
    '''
    basePos = ephem.Observer()
    # Set observer coordinates
    basePos.lat = "{0:3.4f}".format(baseInfo['lat'])
    basePos.lon = "{0:3.4f}".format(baseInfo['long'])
    return basePos

def findPass(start_time: datetime.date, basePos: ephem.Observer) -> tuple[datetime.date, datetime.date, datetime.timedelta, float]:
    '''
    Finds the next pass from the specified start time and ground station.
    '''
    AoS = start_time
    LoS = start_time
    visible_flag = False
    
    # Go to next AoS
    for i in range(86400) : 
        basePos.date = start_time + datetime.timedelta(seconds=i)
        satellite.compute(basePos)
        if math.degrees(satellite.alt) > 0:
            AoS = start_time + datetime.timedelta(seconds=i)
            break
    
    # Go to next LoS
    for i in range(1800) : 
        basePos.date = AoS + datetime.timedelta(seconds=i)
        satellite.compute(basePos)
    
        if math.degrees(satellite.alt) > 0 : 
            visible_flag = True
        else : 
            if visible_flag == True : 
                LoS = AoS + datetime.timedelta(seconds=i)
                visible_flag = False
    
    duration = (LoS - AoS)
    
    max_elevation = 0.0
    # Find max elevation of pass
    for i in range(int(duration.total_seconds())):
        basePos.date = AoS + datetime.timedelta(seconds=i)
        satellite.compute(basePos)
        if math.degrees(satellite.alt) > max_elevation:
            max_elevation = math.degrees(satellite.alt)
        else:
            break
    
    return AoS, LoS, duration, max_elevation

def makeEvent(satData: dict, op: dict, AoS: datetime.datetime, LoS: datetime.datetime, max_elevation: float) -> dict:
    '''
    Makes a Google Calendar event from the given info.
    Also returns the operator for that event.
    '''
    # Make event dict
    event = {
        'summary': satData.get('name') + ' {:.1f}° '.format(max_elevation) + op.get('operationType'),
        'description': op.get('mailDescription'),
        'start': {
            'dateTime': AoS.astimezone(timezone('Asia/Tokyo')).isoformat(),
            'timeZone': 'Asia/Tokyo',
        },
        'end': {
            'dateTime': LoS.astimezone(timezone('Asia/Tokyo')).isoformat(),
            'timeZone': 'Asia/Tokyo',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 1*60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    try:
        # Get next operator
        operator = op['operators'].pop(0)
        op['operators'].append(operator)
        event['attendees'] = [operator]
    except:
        operator = None


    return event, operator

def getGCalendarCreds(tokenLoc: str) -> Credentials:
    '''
    Gets the credetials required for Google Calendar API.
    '''
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(tokenLoc):
        creds = Credentials.from_authorized_user_file(tokenLoc, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                './credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(tokenLoc, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def makeOutput(operator: dict, AoS: datetime.date, LoS: datetime.date, duration: datetime.timedelta, max_elevation: float, idx: int) -> list:
    '''
    Packages the required info into a list for table output.
    '''
    row = []
    row.append(idx)
    row.append(AoS.astimezone(timezone('Asia/Tokyo')).strftime("%Y/%m/%d, %H:%M:%S"))
    row.append(LoS.astimezone(timezone('Asia/Tokyo')).strftime("%Y/%m/%d, %H:%M:%S"))
    row.append(duration)
    row.append(max_elevation)
    try:
        row.append(operator.get('email'))
    except:
        row.append("None")

    return row

####################
# Main Program
####################

if __name__ == "__main__":
    # File locations
    settingsLoc = "./settings.json"
    tokenLoc = "./token.json"

    # Create empty dicts
    settings = dict()
    satList = dict()
    baseInfo = dict()

    # Load settings from file
    settings = getSettings(settingsLoc)

    # Load base station info and make pyephem observer
    baseInfo = settings.get('baseStation')
    basePos = makeObserver(baseInfo)

    # Fetch TLE data and load list of satellites from settings
    satList = getTLE(settings.get('satellites'), saveTLE=True)

    # Get list of all operations to cosider
    opsList = list(settings.get('operations'))

    # Make Google Calendar Credentials
    try:
        creds = getGCalendarCreds(tokenLoc)
        service = build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print("Failed to build calendar service!\n", e)
        exit()

    # Get today's date and find beginning of week
    today = datetime.date.today()
    begin_of_week = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days = _delta_week * 7)

    # Loop for each satellite in list
    for op in opsList:
        print(op.get("operationType"))
        satData = satList.get(op.get('satID'))
        idx = 0
        output = []

        # Get current time and set LoS
        current_time = datetime.datetime.combine(begin_of_week, datetime.time(hour=0,minute=0,tzinfo=timezone('UTC'))) - datetime.timedelta(hours=9)
        LoS = current_time

        # Create satellite object from TLE
        try:
            tle = satData['TLE']
        except:
            print("No TLE data for ", satData.get('name'))
            continue
        satellite = ephem.readtle(op.get('satID'), tle[0], tle[1])

        # Do while LoS - current_time is less than or equal to _total_duration
        validTimeDelta = True
        while validTimeDelta:
            # Find next pass
            AoS, LoS, duration, max_elevation = findPass(LoS, basePos)
            # Check if max_elevation is below value for satellite minElevation
            if(max_elevation >= op.get('minElevation')):
                idx += 1
                # Make calendar event and output
                event, operator = makeEvent(satData, op, AoS, LoS, max_elevation)
                output.append(makeOutput(operator, AoS, LoS, duration, max_elevation, idx))
                # Commit changes to Google Calendar
                if _commitChanges is True:
                    try:
                        event = service.events().insert(calendarId=op.get('calendar_id'), sendNotifications=True, body=event).execute()
                        print('Events created: %d' % idx, end='\r')
                    except HttpError as error:
                        print('An error occurred: %s' % error)
                        exit()
            validTimeDelta = ((LoS - current_time).total_seconds() <= _total_duration)  # Set exit flag
        # Output table of passes for satellite
        print()
        print(tabulate(output, headers=["No.","AOS", "LOS", "Duration", "Max Elevation", "Operator"]),'\n')

