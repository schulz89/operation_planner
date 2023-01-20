import json
import ephem
import math
import datetime
import os
import urllib.request

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TLE_URL = "http://celestrak.org/NORAD/elements/stations.txt"
SCOPES = ['https://www.googleapis.com/auth/calendar']
_commitChanges = True
_delta_week = 0

def getSettings(filename: str) -> dict:
    with open(filename) as json_file:
        return json.load(json_file)

def getTLE(satList: dict) -> dict:
    tle_data = urllib.request.urlopen(TLE_URL).read().decode()
    tle_data = tle_data.split('\r\n')
    for i in range(0, len(tle_data), 3):
        if tle_data[i].rstrip() in satList.keys():
            satList[tle_data[i].rstrip()]['TLE'] = [tle_data[i+1].rstrip(), tle_data[i+2].rstrip()]
    return satList

def makeObserver(baseInfo: dict) -> ephem.Observer:
    basePos = ephem.Observer()
    basePos.lat = "{0:3.4f}".format(baseInfo['long'])
    basePos.lon = "{0:3.4f}".format(baseInfo['long'])
    return basePos

def find_pass(start_time, basePos):
    AoS = start_time
    LoS = start_time
    visible_flag = False
    
    #go to next AoS
    for i in range(24*60*60) : 
        basePos.date = start_time + datetime.timedelta(seconds=i)
        satellite.compute(basePos)
    
        if math.degrees(satellite.alt) > 0:
            AoS = start_time + datetime.timedelta(seconds=i)
            break
    
    #go to next LoS
    for i in range(30*60) : 
        basePos.date = AoS + datetime.timedelta(seconds=i)
        satellite.compute(basePos)
    
        if math.degrees(satellite.alt) > 0 : 
            visible_flag = True
        else : 
            if visible_flag == True : 
                LoS = AoS + datetime.timedelta(seconds=i)
                visible_flag = False
    
    duration = (LoS - AoS)
    
    max_elevation = 0
    for i in range(int(duration.total_seconds())):
        basePos.date = AoS + datetime.timedelta(seconds=i)
        satellite.compute(basePos)
        if math.degrees(satellite.alt) > max_elevation:
            max_elevation = math.degrees(satellite.alt)
        else:
            break
    
    return AoS, LoS, duration, max_elevation

def makeEvent(satData: dict, AoS: datetime.datetime, LoS: datetime.datetime) -> dict:
    event = {
        'summary': satData['name'] + ' {:.1f}° '.format(max_elevation) + satData['operationTpye'],
        'description': satData['mailDescription'],
        'start': {
            'dateTime': AoS.astimezone(datetime.timezone(name='Asia/Tokyo')).isoformat(),
            'timeZone': 'Asia/Tokyo',
        },
        'end': {
            'dateTime': LoS.astimezone(datetime.timezone(name='Asia/Tokyo')).isoformat(),
            'timeZone': 'Asia/Tokyo',
        },
        'attendees': satData['operators'],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 1*60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    return event

def getGCalendarCreds(tokenLoc: str) -> Credentials:
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
                '../credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(tokenLoc, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def makeOutputString(opList, AoS, LoS, idx):
    operator = opList.pop()
    output_string = ""
    output_string += "{:0}, ".format(idx)
    output_string += AoS.astimezone(datetime.timezone(name='Asia/Tokyo')).strftime("%Y/%m/%d, %H:%M:%S") + ", "
    output_string += LoS.astimezone(datetime.timezone(name='Asia/Tokyo')).strftime("%H:%M:%S") + ", "
    output_string += str(duration) + ", "
    output_string += "{:.2f}, ".format(max_elevation)
    output_string += operator.get('email')

    return output_string

if __name__ == "__main__":
    settingsLoc = "../settings.json"
    tokenLoc = "../token.json"
    settings = dict()
    satList = dict()
    baseInfo = dict()

    #download TLE file
    settings = getSettings(settingsLoc)
    baseInfo = settings['baseStation']
    basePos = makeObserver(baseInfo)
    satList = getTLE(settings['satellites'])

    try:
        creds = getGCalendarCreds(tokenLoc)
        service = build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print("Failed to build calendar service!\n", e)
        exit()

    today = datetime.date.today()
    begin_of_week = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days = _delta_week * 7)
    total_duration = 7*24*60*60 # a week

    current_time = datetime.datetime.combine(begin_of_week, datetime.time(hour=0,minute=0,tzinfo=datetime.timezone(name="Asia/Tokyo")))
    LoS = current_time
    
    print("No., Date, AOS, LOS, Duration, Max. el., Operator")

    for ID, satData in satList.items():
        tle = satData['TLE']
        satellite = ephem.readtle(tle[0], tle[1], tle[2])
        idx = 0

        while (LoS - current_time).total_seconds() >= total_duration:
            AoS, LoS, duration, max_elevation = find_pass(LoS, basePos)
            opList = satData['operators']
            if(max_elevation >= satData['minElevation']):
                idx += 1
                output = makeOutputString(opList, AoS, LoS, idx)
                print(output)
                event = makeEvent(satData, AoS, LoS)
                if _commitChanges is True:
                    try:
                        event = service.events().insert(calendarId=satData.get('calendar_id'), sendNotifications=True, body=event).execute()
                        print('Event created: %s' % (event.get('htmlLink')))
                    except HttpError as error:
                        print('An error occurred: %s' % error)

