import json


with open('data/mappings.json', 'r') as file:
    mappings = json.loads(file.read())
    templar2num = mappings['templar2num']
    num2templarmod = mappings['num2templarmod']
    modtranslation2num = mappings['modtranslation2num']
    num2explicitmod = mappings['num2explicitmod']

with open('data/useful_seeds', 'r') as file:
    useful_seeds = set(json.loads(file.read()))