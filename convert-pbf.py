#!/usr/bin/env python

import argparse
import csv
import json
import math
import os

from imposm.parser import OSMParser

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--state', help='state to use in edges and vertices', default='CA')
parser.add_argument('--vertex', help='name of the vertex collection', default='V')
parser.add_argument('--edge', help='name of the edge collection', default='E')

args = parser.parse_args()

allNodes = dict()
allEdges = set()
allCoords = dict()
seenNodes = dict()
seenEdges = set()

vertFile = open(args.vertex + '-' + args.state + '.json', 'w')
edgeFile = open(args.edge + '-' + args.state + '.json', 'w')

if os.path.isfile('mapping.csv'):
    with open('mapping.csv', 'r') as csvfile:
        mapping = csv.reader(csvfile, delimiter=',', quotechar='\\')

        for row in mapping:
            if row[0] == 'N':
                seenNodes[int(row[1])] = row[2]
            elif row[0] == 'E':
                seenEdges.add(int(row[1]))

    csvfile.close()

mapFile = open('mapping.csv', 'a')

prefix = args.vertex + '/'

def distance(lat1, lon1, lat2, lon2):
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    dlon = math.radians(dlon)
    dlat = math.radians(dlat)
    r = 6378137
    a = math.pow(math.sin(dlat/2),2) + math.cos(lat1)*math.cos(lat2)*math.pow(math.sin(dlon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return c * r

def distanceInMiles(slat, slon, dlat, dlon):
    earthRadius = 3958.75
    xlat = math.radians(dlat - slat)
    xlon = math.radians(dlon - slon)
    sindLat = math.sin(xlat / 2)
    sindLon = math.sin(xlon / 2)
    a = math.pow(sindLat, 2) + math.pow(sindLon, 2) * math.cos(math.radians(slat)) * math.cos(math.radians(dlat))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earthRadius * c

def ways(elems):
    for osmid, tags, refs in elems:
        if not 'highway' in tags:
            continue

        if len(refs) == 0:
            continue

        allEdges.add(osmid)

        for ref in refs:
            if ref in allNodes:
                allNodes[ref] += 1
            else:
                allNodes[ref] = 1

        allNodes[refs[0]] += 1
        allNodes[refs[-1]] += 1

def vertices(elems):
    for osmid, attr, coord in elems:
        if osmid not in allNodes:
            continue

        if allNodes[osmid] < 2:
            continue

        if osmid not in seenNodes:
            key = args.state + ':' + str(osmid)
            seenNodes[osmid] = key
            mapFile.write('N,' + str(osmid) + ',' + key + ',N,' + args.state + '\n')
        else:
            continue

        obj = dict()
        obj['_key'] = seenNodes[osmid]
        obj['osmid'] = osmid
        obj['coord'] = coord
        obj['state'] = args.state

        if 'highway' in attr:
            obj['type'] = attr['highway']

        for k in [ 'name', 'natural' ]:
            if k in attr:
                obj[k] = attr[k]

        vertFile.write(json.dumps(obj) + '\n')

def coords(elems):
    for osmid, lon, lat in elems:
        allCoords[osmid] = (lon, lat)

        if osmid not in allNodes:
            continue

        if allNodes[osmid] < 2:
            continue

        if osmid not in seenNodes:
            key = args.state + ':' + str(osmid)
            seenNodes[osmid] = key
            mapFile.write('N,' + str(osmid) + ',' + key + ',C,' + args.state + '\n')
        else:
            continue

        obj = dict()
        obj['_key'] = seenNodes[osmid]
        obj['coord'] = (lon, lat)
        obj['osmid'] = osmid
        obj['state'] = args.state
        obj['type'] = 'coord'

        vertFile.write(json.dumps(obj) + '\n')

def edges(elems):
    for osmid, tags, refs in elems:
        if osmid not in allEdges:
            continue

        if osmid in seenEdges:
            continue

        seenEdges.add(osmid)
        mapFile.write('E,' + str(osmid) + ',' + args.state + '\n')

        first = None
        left = None
        right = None
        miles = 0

        for ref in refs:
            if first == None:
                first = ref
                left = allCoords[ref]
                continue

            right = allCoords[ref]
            dist = distanceInMiles(left[0], left[1], right[0], right[1])
            miles += dist

            left = right

            if allNodes[ref] > 1:
                obj = dict();
                obj['_from'] = prefix + seenNodes[first]
                obj['_to'] = prefix + seenNodes[ref]
                obj['state'] = args.state
                obj['osmid'] = osmid
                obj['miles'] = miles

                if 'highway' in tags:
                    obj['type'] = tags['highway']

                for k in [ 'name', 'lanes', 'access', 'oneway', 'bridge' ]:
                    if k in tags:
                        obj[k] = tags[k]

                edgeFile.write(json.dumps(obj) + '\n')

                first = ref
                miles = 0

C = 1

p1 = OSMParser(concurrency=C, ways_callback=ways)
p1.parse(args.file)

p2 = OSMParser(concurrency=C, nodes_callback=vertices)
p2.parse(args.file)

p3 = OSMParser(concurrency=C, coords_callback=coords)
p3.parse(args.file)

p4 = OSMParser(concurrency=C, ways_callback=edges)
p4.parse(args.file)
