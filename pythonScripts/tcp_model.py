# Model for Section 5 (TCP)

import os
import sys
import pandas as pd
from findLoss import findLossReno, findLossCubic
from calcTx import calcTxReno, calcTxCubic, calcTxHB
from multiprocessing import Pool
from statistics import median

import numpy as np
import time
np.set_printoptions(threshold=np.inf)


def processFile(filename):

    conn = filename.split('_')[1]

    filename = dataFolder + filename
    print("Processing file: " + filename + str([fbWindow, hbWindow, freqUpdate, testWindow]))

    cc = dataFolder.split('/')[-3]

    if cc == "reno":
        N = 1000
    else:
        N = 100

    # Modeling parameters:
    iterNum = 1000

    # Return error
    txError = []
    latError = []
    # scwnds = []
    txSizes = []

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

                xputOB.append(txBytes / packetSize / hbWindow)

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

            # # # todo: patch (if predicted duration too small) -- weighted average: econ + hb
            # frac = min(1, duration / testWindow)
            # if frac < 0.25:
            #     # print(frac)
            #     econ = econ * 0.25 + ls * 0.75
            #     txPred[0] = econ

            txBytes = sndnxt[idxTest[-1]] - sndnxt[idxTest[0]]
            lat = timestamp[idxTest[-1]] - timestamp[idxTest[0]]

            # todo Error case 4) ignore cycling/delayed updated seq test cases
            if txBytes <= 0:
                continue

            # # todo only for change network condition (take the points around the changing point)
            start = 480
            dur = 120
            curTime = timestamp[idxTest[0]]
            print(curTime)
            if curTime < start or curTime > (start + dur):
                continue

            txPkts = txBytes / packetSize
            latPred = txPkts / txPred
            le = abs(latPred - lat) / lat * 100
            # print("Latency predction: " + str(latPred) + "\nLatency: " + str(lat) + "\nError: " + str(le) + "%")
            latError.append(le)

            tx = txBytes / packetSize / testWindow
            te = abs(tx - txPred) / tx * 100
            # print("Xput predction: " + str(txPred) + "\nXput: " + str(tx) + "\nError: " + str(te) + "%")
            txError.append(te)
            # scwnds.append(scwnd)
            txSizes.append(txBytes / 1024 / 1024)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Error in file " + filename + " -- " + str(i + 1) + "th iteration: ")
            print(e, fname, exc_tb.tb_lineno)

    if not len(txError) or not len(latError):
        return
    else:
        txError = np.vstack(txError)
        latError = np.vstack(latError)
        # scwnds = np.vstack(scwnds)
        txSizes = np.vstack(txSizes)
        # conns = np.ones((txError.shape[0], 1)) * int(conn)
        return np.hstack((txError, latError, txSizes))


if __name__ == "__main__":

    t0 = time.time()

    dataFolders = [
                   # cubic
                   # "/mnt/ssd/sigm19data/cubic/korea_cubic/",
                   # "/mnt/ssd/sigm19data/cubic/clemson_cubic/",
                   # "/mnt/ssd/sigm19data/cubic/lab_cubic_sigm19_2/",
                   # "/mnt/ssd/sigm19data/cubic/azure_cubic/",
                   # "/mnt/ssd/sigm19data/cubic/rutgers_cubic/",
                   # "/mnt/ssd/sigm19data/cubic/wireless_cubic/",

                   # reno
                   # "/mnt/ssd/sigm19data/reno/uw_reno/",
                #    "/mnt/ssd/sigm19data/reno/clemson_reno/",
                   # "/mnt/ssd/sigm19data/reno/lab_reno_sigm19/",
                   # "/mnt/ssd/sigm19data/reno/azure_reno/",
                   # "/mnt/ssd/sigm19data/reno/rutgers_reno/",
                   # "/mnt/ssd/sigm19data/reno/wireless_reno/",

                   # change network (reno)
                   "/mnt/ssd/sigm19data/reno/netchange_reno/",
                   # "/mnt/ssd/sigm19data/cubic/netchange_cubic/"
    ]

    for dataFolder in dataFolders:
        cc = dataFolder.split('/')[-3]

        filenames = []
        for f in os.listdir(dataFolder):
            if "_2" in f:
            # nc = "p_inc"
            # nc = "p_dec"
            # nc = "rtt_inc"
            # nc = "rtt_dec"
            # if nc in f:
            # if "data" in f:
                filenames.append(f)
        print(filenames)

        # Sliding window
        # testcase = [(100, 10, 10, 1), (100, 10, 10, 5), (100, 10, 10, 10)]
        testcase = [(100, 10, 10, 1)]
        for fbWindow, hbWindow, freqUpdate, testWindow in testcase:
            with Pool(20) as p:
                res = p.map(processFile, filenames)
                res = [x for x in res if x is not None]
                res = np.vstack(res)
            print(res)
            modelNum = len(res[0]) // 2
            print("Model num: " + str(modelNum))
            txErrorCDF = res[:, :modelNum]
            print(np.mean(txErrorCDF, axis=0))
            print(np.median(txErrorCDF, axis=0))
            print(np.percentile(txErrorCDF, 25, axis=0))
            print(np.percentile(txErrorCDF, 75, axis=0))
            latErrorCDF = res[:, modelNum:]

            if cc == "reno":
                dfXput = pd.DataFrame(txErrorCDF, columns=['econ', 'pftk', 'pftkc', 'pftkr', 'ewma', 'hw', 'ls', 'hm'])
                dfLat = pd.DataFrame(latErrorCDF, columns=['econ', 'pftk', 'pftkc', 'pftkr', 'ewma', 'hw', 'ls', 'hm', 'size'])
            else:
                dfXput = pd.DataFrame(txErrorCDF, columns=['econ', 'ewma', 'hw', 'ls', 'hm'])
                dfLat = pd.DataFrame(latErrorCDF, columns=['econ', 'ewma', 'hw', 'ls', 'hm', 'size'])

            win = "_FB:" + str(fbWindow) + "-HB:" + str(hbWindow) + "-UP:" + str(freqUpdate) + "-PRE:" + str(testWindow)

            # dfXput.to_csv(os.path.join("./results/", dataFolder.split("/")[-2] + win + "_txError_" + nc + ".csv"), sep=",")
            dfXput.to_csv(os.path.join("./results/", dataFolder.split("/")[-2] + win + "_txError.csv"), sep=",")
            dfLat.to_csv(os.path.join("./results/", dataFolder.split("/")[-2] + win + "_latError.csv"), sep=",")

            print("Elapse time: " + str(time.time() - t0) + "s")
            print("Test Cases: " + str(txErrorCDF.shape) + "; " + str(latErrorCDF.shape))