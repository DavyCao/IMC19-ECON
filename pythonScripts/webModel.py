# Model for Section 6 (Web)

import os
import json
from calcTx import calcTxCubic, calcTxSS, getCubicCwnd
from pprint import pprint
import copy
import sys
import numpy as np
from numpy import genfromtxt
import time


class connection:
    def __init__(self, rtt):
        # const
        self.rtt = rtt

        # state
        self.slowStart = True

        # Trapezoid start and end cwnd size
        self.scwnd = 10
        self.nxtLossCwnd = -1

        # model paras
        self.xput = -1
        self.cwnd = self.scwnd

        # Update parameters
        self.updateTime = -1
        self.reqUpdate = True

        # workload
        self.load = 0

    def reset(self):
        self.load = 0


class stream:
    def __init__(self, idx):
        self.idx = idx
        self.obj = None
        self.load = 0

    def reset(self):
        self.obj = None
        self.load = 0

    def add(self, obj):
        self.obj = obj
        self.load = self.obj["transferSize"]


class h1Connection(connection):
    def __init__(self, idx, rtt):
        connection.__init__(self, rtt)
        self.obj = None
        self.connIdx = idx

    def reset(self):
        connection.reset(self)
        self.obj = None

    def add(self, obj):
        self.obj = obj
        self.load = self.obj["transferSize"]


class h2Connection(connection):
    def __init__(self, rtt):
        connection.__init__(self, rtt)
        self.streams = set()
        self.hiStream = -1

    def reset(self):
        for s in self.streams:
            s.reset()

    def addStream(self, obj):
        s = stream(self.hiStream + 1)
        s.add(obj)
        self.streams.add(s)
        self.hiStream += 1

    def delStream(self, s):
        self.streams.remove(s)


# getTiming for fake pages
# def getTiming():
#     objSkipped = 0
#     objTotal = 0
#
#     logs = [[], [], [], []]
#     webSize = 0
#     with open(folder + filename) as f:
#         data = json.load(f)
#
#     for item in data:
#         if "id" in item and "objs" in item:
#             # Find the network event for the "id"
#             objs = item["objs"]
#             for obj in objs:
#                 if "activityId" in obj and "Networking" in obj["activityId"]:
#                     objTotal += 1
#                     if "transferSize" not in obj:
#                         objSkipped += 1
#                         continue
#                     record = {
#                         "name": item["id"],
#                         "transferSize": obj["transferSize"] / packetSize * 1000,
#                         "latency": (obj["responseReceivedTime"] - obj["startTime"]) / 1000,
#                         "latencyPred": -1
#                     }
#
#                     if "demo.html" in item["id"]:
#                         logs[0].append(record)
#                     elif "styles.css" in item["id"] or "firstScript.js" in item["id"]:
#                         logs[1].append(record)
#                     elif "imgScript.js" in item["id"]:
#                         logs[2].append(record)
#                     else:
#                         logs[3].append(record)
#                     webSize += obj["transferSize"]
#     print("\nWeb page size: " + str(webSize) + " Bytes. " + str(objTotal) + " objs in total, " + str(objSkipped) + " objs skipped.")
#     return logs


# getTiming for real pages
def getTiming():
    objSkipped = 0
    objTotal = 0
    comp = 0

    logs = [[] for _ in range(1000)]
    webSize = 0

    with open(folder + filename + ".har") as f:
        har = json.load(f)

    dic = {}
    # Go over the har file and get actual size of objects
    for i in range(len(har['log']['entries'])):
        actualURL = har['log']['entries'][i]['request']['url'].replace('http://', '').replace('https://', '')
        actualSize = har['log']['entries'][i]['response']['_transferSize']
        dic[actualURL] = actualSize

    with open(folder + filename) as f:
        data = json.load(f)

    deps = set(data[-1]["criticalPath"])

    for item in data:
        if "id" in item and "objs" in item:
            # Find the network event for the "id"
            objs = item["objs"]
            for obj in objs:
                if "activityId" in obj:
                    if "Networking" not in obj["activityId"]:
                        if obj["activityId"] in deps:
                            # Non-networking critical path obj
                            comp += (obj["endTime"] - obj["startTime"]) / 1000
                    else:
                        objTotal += 1
                        if "segmentIdx" not in obj or \
                                item["id"].replace('http://', '').replace('https://', '') not in dic.keys() \
                                or dic[item["id"].replace('http://', '').replace('https://', '')] == 0:
                            objSkipped += 1
                            continue

                        obj["transferSize"] = dic[item["id"].replace('http://', '').replace('https://', '')]
                        record = {
                            "name": item["id"],
                            "transferSize": obj["transferSize"] / packetSize,
                            "segmentIdx": obj["segmentIdx"],
                            # "latency": (obj["responseReceivedTime"] - obj["startTime"]) / 1000,
                            "latencyPred": -1
                        }

                        idx = obj["segmentIdx"]
                        logs[idx].append(record)
                        webSize += obj["transferSize"]
    print("\nWeb page size: " + str(webSize) + " Bytes. " + str(objTotal) + " objs in total, "
          + str(objSkipped) + " objs skipped. Computation time: " + str(comp) + "s")
    return [comp, logs]


def http1(phaseIdx, log):
    returnLog = []
    # Count the number of objects to be fetched
    objNum, completed = len(log), 0
    # print("\n" + str(objNum) + " objects to fetch, generating connections pool..")

    # Get # connections required
    numConnReq = min(objNum, h1MaxConn)
    for idx in range(numConnReq):
        h1Pool[idx].add(log.pop(0))

    # print("\nConnection status after initialization: ")
    # for c in h1Pool:
    #     print(c.__dict__)

    # Evolution on round trips:
    # print("----- HTTP/1.1 Modeling Starts (Phase " + str(phaseIdx) + ") -----")
    curTime, rt = 0, 1
    while completed < objNum:
        # check how many parallel downloads
        npc = sum([c.load > 0 for c in h1Pool])
        # print("----- " + str(rt) + "th round trip; " + str(npc) + " connections busy ---")

        # check each connection
        for c in h1Pool:
            if not c.load:
                continue

            # todo check when to update
            if c.reqUpdate:
                if c.slowStart:
                    c.xput = c.cwnd / c.rtt
                    _, _, c.nxtLossCwnd = calcTxSS(rounds=ssRounds, pcwnd=pcwnds[npc - 1], rtt=rtt)
                else:
                    c.xput, _, c.nxtLossCwnd = calcTxCubic(scwnd=c.cwnd, rounds=rounds, pcwnd=pcwnds[npc - 1], rtt=rtt)
                c.scwnd = c.cwnd
                c.updateTime = curTime
                c.reqUpdate = False

            # todo print connection status
            # print(c.__dict__)

            txPred = c.xput * c.rtt

            # print("cwnd: " + str(c.cwnd) + "; estimated transfer: " + str(txPred))

            eTime = curTime + rtt
            # Check if download can finish, if so, increase counter, add new obj
            if txPred >= c.load:
                # print("Job complete!\n")
                completed += 1
                # Record the latency prediction
                obj = c.obj
                obj["latencyPred"] = eTime * 1000
                returnLog.append(obj)
                # Add new obj
                c.reset()
                if len(log):
                    c.add(log.pop(0))
            else:
                c.load -= txPred
                # print("Job in progresss..\n")

            # update cwnd if txPred > c.cwnd
            if txPred >= c.cwnd:
                if c.slowStart:
                    targetCwnd = c.cwnd * 2
                else:
                    targetCwnd = getCubicCwnd(t=eTime-c.updateTime, scwnd=c.scwnd)
                # If we predict loss will occur
                if targetCwnd > c.nxtLossCwnd:
                    c.cwnd = targetCwnd * 0.7
                    c.reqUpdate = True
                    if c.slowStart:
                        c.slowStart = False
                else:
                    c.cwnd = targetCwnd
                    if c.slowStart:
                        c.xput = c.cwnd / c.rtt

        curTime += rtt
        rt += 1

    # print("----- HTTP/1.1 Modeling Finishes (Phase " + str(phaseIdx) + ") -----")
    # print(str(completed) + " objects completed in " + str(curTime) + "seconds")
    return [returnLog, curTime]


def http2(phaseIdx, log):
    returnLog = []
    objNum, completed = len(log), 0
    # print("\n" + str(objNum) + " objects to fetch, generating connections pool..")

    # Get # streams required
    c = h2Pool[0]
    numStreamReq = min(h2StreamNum, objNum)
    for idx in range(numStreamReq):
        c.addStream(log.pop(0))

    # print("\nStream status after initialization: ")
    # pprint([vars(s) for s in c.streams])

    # Evolution on round trips:
    # print("----- HTTP/2 Modeling Starts (Phase " + str(phaseIdx) + ") -----")
    curTime, rt = 0, 1
    while completed < objNum:
        # check how many working streams
        nps = len(c.streams)
        pipeLoad = sum([s.load for s in c.streams])
        # print("----- " + str(rt) + "th round trip; " + str(nps) + " streams busy --- Total load: " + str(pipeLoad))
        # todo check when to update
        if c.reqUpdate:
            if c.slowStart:
                c.xput = c.cwnd / c.rtt
                _, _, c.nxtLossCwnd = calcTxSS(rounds=ssRounds, pcwnd=pcwnds[0], rtt=rtt)
            else:
                c.xput, _, c.nxtLossCwnd = calcTxCubic(scwnd=c.cwnd, rounds=rounds, pcwnd=pcwnds[0], rtt=rtt)
            c.scwnd = c.cwnd
            c.updateTime = curTime
            c.reqUpdate = False

        txPred = c.xput * c.rtt

        # print("cwnd: " + str(c.cwnd) + "; estimated transfer: " + str(txPred))

        eTime = curTime + rtt
        transfered = 0

        # Keep deque streams until txPred have been sent
        rm = set()
        new = 0
        for s in c.streams:
            if transfered >= txPred:
                break
            # If stream can be finished
            if s.load <= (txPred - transfered):
                # print("Stream " + str(s.idx) + " job complete!\n")
                completed += 1
                obj = s.obj
                obj["latencyPred"] = eTime * 1000
                returnLog.append(obj)
                transfered += s.load

                s.reset()
                rm.add(s)

                new += 1

            else:
                s.load -= (txPred - transfered)
                transfered += (txPred - transfered)
                # print("Stream " + str(s.idx) + " job in progress..\n")

        for s in rm:
            c.delStream(s)

        while new > 0 and len(log):
            c.addStream(log.pop(0))
            new -= 1

        # print("\nStream status after " + str(rt) + "th round trip")
        # pprint([vars(s) for s in c.streams])

        # update cwnd if txPred > c.cwnd
        if txPred >= c.cwnd:
            if c.slowStart:
                targetCwnd = c.cwnd * 2
            else:
                targetCwnd = getCubicCwnd(t=eTime - c.updateTime, scwnd=c.scwnd)
            # If we predict loss will occur
            if targetCwnd > c.nxtLossCwnd:
                c.cwnd = targetCwnd * 0.7
                c.reqUpdate = True
                if c.slowStart:
                    c.slowStart = False
            else:
                c.cwnd = targetCwnd
                if c.slowStart:
                    c.xput = c.cwnd / c.rtt

        curTime += rtt
        rt += 1

    # print("----- HTTP/2 Modeling Finishes (Phase " + str(phaseIdx) + ") -----")
    # print("[" + str(completed) + " objects completed in " + str(curTime) + "seconds]")
    return [returnLog, curTime]


def createH1Conn(rtt):
    pool = []
    # print("\nCreating HTTP/1.1 connections...")
    for idx in range(h1MaxConn):
        c = h1Connection(idx=idx, rtt=rtt)
        pool.append(c)
        # print(c.__dict__)
    return pool


def createH2Conn(rtt):
    # print("\nCreating HTTP/2 connection...")
    c = h2Connection(rtt=rtt)
    # print(c.__dict__)
    return [c]


if __name__ == "__main__":
    packetSize = 1448  # todo check
    rtt = 0.05  # todo to be replaced
    p = int(sys.argv[1])
    # pcwnds = [[p] * 10000 for _ in range(6)]  # todo to be replaced
    pcwnds = np.array([[0.0] * 10000 for _ in range(6)])  # todo to be replaced

    for l in range(6):
        fpcwnd = "../sigm19_pcwnd_web/data_" + str(l + 1) + '_p-' + str(p) + ".csv"

        btp = genfromtxt(fpcwnd, delimiter=',')

        for i in range(1, len(btp)):
            cwnd = int(btp[i][1])
            pcwnds[l][cwnd] = btp[i][2]

        mincwnd = int(btp[1][1])
        maxcwnd = int(btp[-1][1])

        for j in range(mincwnd):
            pcwnds[l][j] = pcwnds[l][mincwnd]

        for k in range(maxcwnd + 1, 10000):
            pcwnds[l][k] = pcwnds[l][maxcwnd]

    print("Network conditions --  p 1e-: " + str(p) + "; RTT: " + str(rtt) + "ms")

    h1MaxConn, h2MaxConn, h1StreamNum, h2StreamNum = 6, 1, 1, 128
    rounds, ssRounds = 100, 10
    protocols = ["h1", "h2"]

    csv = np.zeros((8, 2))

    folder = "../newJson2/"
    # filename = "http1_small.json"
    # filename = "http1_large.json"

    filenames = [
     # Good for HTTP/2
     "marketb.kr.json",
     "tentsuki.jp.json",
     "www.designnotes.co.json",
     "www.tax-news.com.json",
     "www.glovespot.net.json",

     # Good for HTTP/1.1
     "www.colasrail.com.json",
     "www.field.io.json",
     "www.chucksroadhouse.com.json",
     # "http1_small.json",
     # "http1_large.json"
    ]

    tStart = time.time()
    _tStart = time.process_time()

    for idx in range(10):
        for filename in filenames:
            print(time.process_time())
            [comp, logs] = getTiming()
            for protocol in protocols:
                plt = comp
                h1Log, h2Log = [], []

                if protocol == "h1":
                    h1Pool = createH1Conn(rtt=rtt)
                    for phaseIdx in range(len(logs)):
                        if not len(logs[phaseIdx]):
                            continue
                        logCopy = copy.deepcopy(logs[phaseIdx])
                        [returnLogH1, pred] = http1(phaseIdx, logCopy)
                        h1Log += returnLogH1
                        plt += pred
                    print('H1 Log length: ' + str(len(h1Log)))
                    with open(folder + 'h1_' + str(p) + '_' + filename, 'w') as outfile:
                        json.dump(h1Log, outfile)
                    print("Estimated page load time for " + filename + ": " + str(plt) + "s (under " + protocol + ").")
                    csv[filenames.index(filename)][0] = plt

                else:
                    h2Pool = createH2Conn(rtt=rtt)
                    for phaseIdx in range(len(logs)):
                        if not len(logs[phaseIdx]):
                            continue
                        logCopy = copy.deepcopy(logs[phaseIdx])
                        [returnLogH2, pred] = http2(phaseIdx, logCopy)
                        h2Log += returnLogH2
                        plt += pred
                    print('H2 Log length: ' + str(len(h2Log)))
                    with open(folder + 'h2_' + str(p) + '_' + filename, 'w') as outfile:
                        json.dump(h2Log, outfile)
                    print("Estimated page load time for " + filename + ": " + str(plt) + "s (under " + protocol + ").")
                    csv[filenames.index(filename)][1] = plt
    tEnd = time.time()
    _tEnd = time.process_time()
    
    print("Elapse time: " + str(tEnd - tStart) + "s")
    print("Process time: " + str(_tEnd - _tStart) + "s")
    np.savetxt("_timing.csv", csv, fmt='%.2f', delimiter=",")

