#!/usr/bin/env python

import argparse
import json
import math

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

vertFile = open(args.vertex + '.json', 'w')
edgeFile = open(args.edge + '.json', 'w')

prefix = args.vertex + '/'

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

        obj = dict()
        obj['coord'] = coord
        obj['_key'] = 'K' + str(osmid)
        obj['state'] = args.state

        if 'highway' in attr:
            obj['type'] = attr['highway']

        for k in [ 'name', 'natural' ]:
            if k in attr:
                obj[k] = attr[k]

        vertFile.write(json.dumps(obj) + '\n')

        allNodes[osmid] = 0

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

def coords(elems):
    for osmid, lon, lat in elems:
        allCoords[osmid] = (lon, lat)

        if osmid not in allNodes:
            continue

        if allNodes[osmid] < 2:
            continue

        obj = dict()
        obj['coord'] = (lon, lat)
        obj['_key'] = 'K' + str(osmid)
        obj['state'] = args.state
        obj['type'] = 'coord'

        vertFile.write(json.dumps(obj) + '\n')

def edges(elems):
    for osmid, tags, refs in elems:
        if osmid not in allEdges:
            continue

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
                obj['state'] = args.state
                obj['_from'] = prefix + 'K' + str(first)
                obj['_to'] = prefix + 'K' + str(ref)
                obj['miles'] = miles

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

p3 = OSMParser(concurrency=C, coords_callback=coords, ways_callback=edges)
p3.parse(args.file)
