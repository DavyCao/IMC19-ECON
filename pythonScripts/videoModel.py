# Model for Section 7 (Video)

import os
import sys
import pandas as pd
from findLoss import findLossReno, findLossCubic
from calcTx import calcTxReno, calcTxCubic, calcTxHB
from pprint import pprint
from multiprocessing import Pool
from statistics import median

import numpy as np
import time
np.set_printoptions(threshold=np.inf)


def processFile(filename):

    filename = dataFolder + filename
    print("\nProcessing file: " + filename + str([fbWindow, hbWindow, freqUpdate, testWindow]))

    cc = 'cubic'

    if cc == "reno":
        N = 1000
    else:
        N = 100

    # Modeling parameters:
    iterNum = 10000

    # todo Find the latency of the last segment
    # Read the data using pandas
    df_ = pd.read_csv(filename[:-4] + "_full.txt", header=None, delim_whitespace=True, usecols=[0, 3, 4, 6, 9],
                      names=["time", "src", "dst", "length", "snd_nxt", "snd_una",
                      "cwnd", "ssthresh", "snd_wnd", "srtt", "rcv_wnd"])

    timestamp_ = df_['time'].values
    length_ = df_['length'].values.astype(int)
    sndnxt_ = df_['snd_nxt'].apply(int, base=16).values
    cwnd_ = df_['cwnd'].values.astype(int)
    df_ = None

    eSeq = sndnxt_[-1]
    eTime = timestamp_[-1]

    for l in reversed(range(len(sndnxt_))):
        if sndnxt_[l] + fSize["1080p"] < eSeq or length_[l] == 159:
            break
    sSeq = sndnxt_[l + 1]
    sTime = timestamp_[l + 1]
    latActual = eTime - sTime
    scwndActual = cwnd_[l + 1]

    # Read the data using pandas
    df = pd.read_csv(filename, header=0)
    timestamp = df['time'].values
    sndnxt = df['snd_nxt'].values
    cwnd = df['cwnd'].values.astype(int)
    srtt = df['srtt'].values
    df = None

    # Get packetSize
    i = 1
    while sndnxt[i] <= sndnxt[i - 1]:
        i += 1
    segmentSize = sndnxt[i] - sndnxt[i - 1]

    div, packetSize, i = 1, segmentSize, None
    while packetSize > 1500:
        div += 1
        packetSize = segmentSize / div
    # print("Packet Size: " + str(packetSize) + " Bytes")

    pcwnd = None

    # Initialize HB parameters
    xputOB = []
    ewma = 0
    lt, tt = 0, 0

    for i in range(iterNum):
        try:
            fbTrainStart = i
            trainEnd = fbTrainStart + fbWindow
            hbTrainStart = trainEnd - hbWindow
            testStart = trainEnd
            testEnd = testStart + testWindow

            # todo update frequency = 10s | HB predictors + pcwnd
            if i % freqUpdate == 0 or pcwnd is None:
                idxFbTrain = np.where(np.logical_and(timestamp >= fbTrainStart, timestamp < trainEnd))[0]
                idxHbTrain = np.where(np.logical_and(timestamp >= hbTrainStart, timestamp < trainEnd))[0]

                # todo Error case 0) ignore training cases which has no training data
                if not len(idxFbTrain) or not len(idxHbTrain):
                    pcwnd = None
                    continue

                if cc == "reno":
                    [pcwnd, p, sIdx, eIdx] = findLossReno(cwnd=cwnd[idxFbTrain])
                else:
                    [pcwnd, sIdx, eIdx] = findLossCubic(cwnd=cwnd[idxFbTrain])

                rtt = np.median(srtt[idxFbTrain][-10:]) / 1e6
                txBytes = sndnxt[idxHbTrain[-1]] - sndnxt[idxHbTrain[0]]

                # todo Error case 1) ignore training cases which has no loss or no changing snd_nxt
                if not len(sIdx) or not len(eIdx) or txBytes == 0:
                    pcwnd = None
                    continue

                # todo Error case 2) increase seq if cycling happens during training
                if txBytes < 0:
                    # print("Cycle: " + str(sndnxt[idxTrain[0]]) + "-" + str(sndnxt[idxTrain[-1]]))
                    txBytes += int("ffffffff", 16)

                # todo Video patch, calculate the actual transfer time during HB (removing idle part)
                idxHbTrainFull = np.where(np.logical_and(timestamp_ >= hbTrainStart, timestamp_ < trainEnd))[0]
                _t = timestamp_[idxHbTrainFull]
                p, q, actualHBLen = 0, 1, 0
                while p < len(_t) and q < len(_t):
                    while q < len(_t) and _t[q] - _t[q - 1] < 0.2:
                        q += 1
                    actualHBLen += (_t[q - 1] - _t[p])
                    if q == len(_t):
                        break
                    else:
                        p = q
                        q = p + 1
                # print(actualHBLen)

                xputOB.append(txBytes / packetSize / actualHBLen)

                [ls, hm, ewma, ft, lt, tt] = calcTxHB(ewma=ewma, xputOB=xputOB, lt=lt, tt=tt)

            # For testing, take the start cwnd, and the median rtt of previous 10 samples
            idxTest = np.where(np.logical_and(timestamp >= testStart, timestamp < testEnd))[0]

            # todo Error case 3) ignore empty test slots
            if len(idxTest) == 0:
                continue

            scwnd = cwnd[idxTest[0]]

            if cc == "reno":
                ret = calcTxReno(scwnd=scwnd, rounds=N, pcwnd=pcwnd, p=p, rtt=rtt)
                [econ, pftk, pftkc, pftkr, duration, _] = ret
                txPred = np.array([econ, pftk, pftkc, pftkr, ewma, ft, ls, hm])
            else:
                ret = calcTxCubic(scwnd=scwnd, rounds=N, pcwnd=pcwnd, rtt=rtt)
                [econ, duration, _] = ret
                txPred = np.array([econ, ewma, ft, ls, hm])

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error in file " + filename + " -- " + str(i + 1) + "th iteration: ")
            print(e, fname, exc_tb.tb_lineno)

    return [txPred, latActual, packetSize]


if __name__ == "__main__":

    model = ["ECON", "EWMA", "HW", "LS", "HM"]
    fSize = {"1080p": 1086980, "720p": 527676, "480p":306003, "360p": 244931}  # todo add the size of the 101th video segment
    row = {"50": 0, "100": 1, "150": 2, '200': 3}
    col = {"e2": 0}
    dur = 3.1  # todo add the length of the 101th video segment
    modelNum = 5
    dataFolders = ["/mnt/ssd/sigm19data/cubic/sigm19Video_cubic/"]

    modelDecision = [[[""] * len(col) for _ in range(len(row))] for _ in range(modelNum)]
    groundTruth = [[""] * len(col) for _ in range(len(row))]

    for dataFolder in dataFolders:
        cc = 'cubic'
        filenames = []
        for f in os.listdir(dataFolder):
            if "video" in f and "full" not in f:
                filenames.append(f)
        print(filenames)

        testcase = [(100, 10, 10, 1)]
        for fbWindow, hbWindow, freqUpdate, testWindow in testcase:
            for filename in filenames:
                rowIdx = row[filename.split('_')[1]]
                colIdx = col[filename.split('_')[2].split('.')[0]]

                [txPred, latActual, packetSize] = processFile(filename)
                txPred = np.array(txPred) * packetSize
                sizePred = txPred * dur

                for idx in range(modelNum):
                    if sizePred[idx] >= fSize["1080p"]:
                        modelDecision[idx][rowIdx][colIdx] = "1080p"
                    elif sizePred[idx] >= fSize["720p"]:
                        modelDecision[idx][rowIdx][colIdx] = "720p"
                    elif sizePred[idx] >= fSize["480p"]:
                        modelDecision[idx][rowIdx][colIdx] = "480p"
                    else:
                        modelDecision[idx][rowIdx][colIdx] = "360p"

                # todo need to add ground truth
                print(latActual)
                if latActual < dur:
                    groundTruth[rowIdx][colIdx] = "1080p"
                else:
                    groundTruth[rowIdx][colIdx] = "Switch"

            for idx in range(modelNum):
                print(model[idx] + str(modelDecision[idx]))
            print(groundTruth)



                #
                # print("Predicted maximum transfersize for the next 3.1s: ", str(sizePred))
                # print("Next segment actual size: " + str(fSize))
                # print((txPred * dur) > fSize)
                # print(latActual < dur)
                #
                # latPred = fSize / txPred
                # print("Next segment actual latency: " + str(latActual))
                # print("Next segment predicted latency: " + str(latPred))
                # latError = (latPred - latActual) / latActual * 100
                # print("Error: " + str(latError))
