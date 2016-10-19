#!/usr/bin/env python

import argparse
import json

from imposm.parser import OSMParser

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--state', help='state to use in edges and vertices', default='CA')
parser.add_argument('--vertex', help='name of the vertex collection', default='V')
parser.add_argument('--edge', help='name of the edge collection', default='E')

args = parser.parse_args()

allNodes = dict()
allEdges = set()

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

def coords(elems):
    for osmid, lon, lat in elems:
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

        for ref in refs:
            if first == None:
                first = ref
                continue

            if allNodes[ref] > 1:
                obj = dict();
                obj['state'] = args.state
                obj['_from'] = prefix + 'K' + str(first)
                obj['_to'] = prefix + 'K' + str(ref)

                for k in [ 'name', 'lanes', 'access', 'oneway', 'bridge' ]:
                    if k in tags:
                        obj[k] = tags[k]

                edgeFile.write(json.dumps(obj) + '\n')

                first = ref

C = 1

p1 = OSMParser(concurrency=C, ways_callback=ways)
p1.parse(args.file)

p2 = OSMParser(concurrency=C, nodes_callback=vertices)
p2.parse(args.file)

p3 = OSMParser(concurrency=C, coords_callback=coords, ways_callback=edges)
p3.parse(args.file)
