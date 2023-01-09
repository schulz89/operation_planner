#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Example code of integration of the PyEphem library with Google Calendar API
# Copyright 2023 Victor Hugo Schulz, Daisuke Nakayama
# Copyright 2023 Google Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import ephem
import os
from pytz import timezone
import datetime
import math
import sys
import subprocess

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Variables

commitChanges = False
delta_week = 0

if sys.argv[1] == "kitsune":
    satelliteName = "KTN"
    tleFileName = "KITSUNE.txt"
    operation_type = ""
    min_elevation = 10
    calendar_id = "REPLACE_WITH_GOOGLE_CALENDAR_ID@group.calendar.google.com"
    mail_description = 'This tracks KITSUNE.'
    operatorsFileName = "operators_list_empty.csv"
elif sys.argv[1] == "birds5":
    satelliteName = "BD5"
    tleFileName = "BIRDS5.txt"
    operation_type = ""
    min_elevation = 10
    calendar_id = "REPLACE_WITH_GOOGLE_CALENDAR_ID@group.calendar.google.com"
    mail_description = 'This tracks BIRDS-5.'
    operatorsFileName = "operators_list_empty.csv"
elif sys.argv[1] == "futaba":
    satelliteName = "FTB"
    tleFileName = "FUTABA.txt"
    operation_type = ""
    min_elevation = 10
    calendar_id = "REPLACE_WITH_GOOGLE_CALENDAR_ID@group.calendar.google.com"
    mail_description = 'This tracks Futaba satellite.'
    operatorsFileName = "operators_list_empty.csv"

else:
    sys.exit(1)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

#constant
NowLat = 33.8958
NowLon = 130.8750
NowPosition = ephem.Observer()
NowPosition.lat = "{0:3.4f}".format(NowLat)
NowPosition.lon = "{0:3.4f}".format(NowLon)
degrees_per_radian = 180.0 / math.pi

#download TLE file
def run_cmd(cmd):
    result = subprocess.run([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.stdout.decode('utf-8')

print(run_cmd("./download_tle.sh"))

#read TLE file
fTyp = [("","*")]
iDir = os.path.abspath(os.path.dirname(__file__))

#operators file
operators = open(operatorsFileName, 'r')

#print(tleFileName)
tle = []
for i,line in enumerate(open(tleFileName, 'r')):
    tle.append(line)
    tle[i] = tle[i].rstrip() #Remove trailing newline code
    
#Delete 0 of the head (such as those taken from Space - Track.org)
for j in range(0,i,3) : 
    if(tle[j][:2] == "0 ") : 
        tle[j] = tle[j][2:]
        
SatelliteNameList = []

for j in range(0,i,3) : 
    SatelliteNameList.append(tle[j])
    
#show TLE
#print(SatelliteNameList[0])

#read TLE
satellite = ephem.readtle(tle[0],tle[1],tle[2])

def find_pass(start_time):
    AOS = start_time
    LOS = start_time
    visible_flag = False
    
    #go to next AOS
    for i in range(24*60*60) : 
        NowPosition.date = start_time + datetime.timedelta(seconds=i)
        satellite.compute(NowPosition)
    
        if (satellite.alt * degrees_per_radian) > 0:
            AOS = start_time + datetime.timedelta(seconds=i)
            break
    
    #go to next LOS
    for i in range(30*60) : 
        NowPosition.date = AOS + datetime.timedelta(seconds=i)
        satellite.compute(NowPosition)
    
        if (satellite.alt * degrees_per_radian) > 0 : 
            visible_flag = True
        else : 
            if visible_flag == True : 
                LOS = AOS + datetime.timedelta(seconds=i)
                visible_flag = False
    
    duration = (LOS - AOS)
    
    max_elevation = 0
    for i in range(int(duration.total_seconds())):
        NowPosition.date = AOS + datetime.timedelta(seconds=i)
        satellite.compute(NowPosition)
        if(satellite.alt * degrees_per_radian) > max_elevation:
            max_elevation = satellite.alt * degrees_per_radian
        else:
            break
    return([AOS, LOS, duration, max_elevation])

def main():


    # ======================================================================
    
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        today = datetime.date.today()
        begin_of_week = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days = delta_week * 7)
        total_duration = 7*24*60*60 # a week
        
        #current_time = datetime.datetime.now(timezone("UTC")) # Current time
        current_time = datetime.datetime.combine(begin_of_week, datetime.time(hour=0,minute=0,tzinfo=timezone('UTC')))     - datetime.timedelta(hours=9)
        LOS = current_time
        
        print("No., Date, AOS, LOS, Duration, Max. el., Operator")
        
        counter = 0

        while True:
            [AOS, LOS, duration, max_elevation] = find_pass(LOS)
            if(LOS - current_time).total_seconds() >= total_duration:
                break
            if(max_elevation >= min_elevation):
                counter += 1
                operator = operators.readline().strip()
                output_string = ""
                output_string += "{:0}, ".format(counter)
                output_string += AOS.astimezone(timezone('Asia/Tokyo')).strftime("%Y/%m/%d, %H:%M:%S") + ", "
                output_string += LOS.astimezone(timezone('Asia/Tokyo')).strftime("%H:%M:%S") + ", "
                output_string += str(duration) + ", "
                output_string += "{:.2f}, ".format(max_elevation)
                output_string += operator
                print(output_string)
                
                # Add event start:
                event = {}
                if operator != "":
                    event = {
                      'summary': satelliteName + ' {:.1f}° '.format(max_elevation) + operation_type,
                      # 'location': 'LaSeine 8F, operation room',
                      'description': mail_description,
                      'start': {
                        'dateTime': AOS.astimezone(timezone('Asia/Tokyo')).isoformat(),
                        'timeZone': 'Asia/Tokyo',
                      },
                      'end': {
                        'dateTime': LOS.astimezone(timezone('Asia/Tokyo')).isoformat(),
                        'timeZone': 'Asia/Tokyo',
                      },
                      'attendees': [
                        {'email': operator},
                      ],
                      'reminders': {
                        'useDefault': False,
                        'overrides': [
                          #{'method': 'email', 'minutes': 6*60},
                          {'method': 'popup', 'minutes': 1*60},
                          {'method': 'popup', 'minutes': 10},
                        ],
                      },
                    }
                else:
                    event = {
                      'summary': satelliteName + ' {:.1f}° '.format(max_elevation) + operation_type,
                      # 'location': 'LaSeine 8F, operation room',
                      'description': mail_description,
                      'start': {
                        'dateTime': AOS.astimezone(timezone('Asia/Tokyo')).isoformat(),
                        'timeZone': 'Asia/Tokyo',
                      },
                      'end': {
                        'dateTime': LOS.astimezone(timezone('Asia/Tokyo')).isoformat(),
                        'timeZone': 'Asia/Tokyo',
                      },
                      'reminders': {
                        'useDefault': False,
                        'overrides': [
                          #{'method': 'email', 'minutes': 9*60},
                          {'method': 'popup', 'minutes': 1*60},
                          {'method': 'popup', 'minutes': 10},
                        ],
                      },
                    }
                if commitChanges == True:
                    event = service.events().insert(calendarId=calendar_id, sendNotifications=True, body=event).execute()
                    print('Event created: %s' % (event.get('htmlLink')))
                    exit
                # Add event end.
                # print(event)

    except HttpError as error:
        print('An error occurred: %s' % error)

if __name__ == '__main__':
    main()
