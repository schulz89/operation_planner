#!/bin/sh

# Example of script to download TLE data from Celestrack and filter specific satellites
# Copyright 2023 Victor Hugo Schulz

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ ! -f stations.txt ] || test "`find stations.txt -mmin +60`"
then
    curl -s http://celestrak.org/NORAD/elements/stations.txt --remote-name
    echo TLE download finished.
fi
grep -A2 "KITSUNE" stations.txt > KITSUNE.txt
grep -A2 "1998-067UN" stations.txt > BIRDS5.txt
grep -A2 "FUTABA" stations.txt > FUTABA.txt
