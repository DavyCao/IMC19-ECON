# Model for pcwnd function

import numpy as np
import sys
import os
np.seterr(invalid='ignore')


def findLossReno(cwnd):
    try:
        # p-cwnd graph
        maxcwnd = max(cwnd) + 1
        loss, seen = np.zeros(maxcwnd), np.zeros(maxcwnd)

        # Two pointers to find start/end point of each trapezoid
        sIdx = []
        eIdx = []
        p, q = 0, 0
        sFlag = False

        while p < len(cwnd) and q < len(cwnd):
            if not sFlag:
                while p + 1 < len(cwnd) and (cwnd[p + 1] - cwnd[p]) != 1:
                    p += 1
                if p + 1 == len(cwnd):
                    break
                else:
                    # todo: check if previous loss is false positive
                    if len(eIdx) and cwnd[p] - cwnd[eIdx[-1]] >= -1:
                        eIdx.pop()
                    else:
                        sIdx.append(p)
                    sFlag = True
                    q = p + 1
                    continue
            else:
                while q + 2 < len(cwnd) and (cwnd[q] < cwnd[q + 1] or  # proceed if 1) increasing
                                             cwnd[q] - cwnd[q - 1] > 2 and cwnd[q] - cwnd[q + 1] > 2 or  # up spike
                                             cwnd[q] - cwnd[q + 1] > 0 and cwnd[q + 2] - cwnd[q + 1] > 0):  # down spike
                    q += 1
                if q + 2 == len(cwnd):
                    break
                else:
                    # todo: check if we should ignore this trapezoid
                    if len(sIdx) and q - sIdx[-1] < 3:
                        sIdx.pop()
                    else:
                        eIdx.append(q)
                    sFlag = False
                    p = q + 1

        if len(sIdx) != len(eIdx):
            sIdx.pop()

        for i in range(len(eIdx)):
            for idx in range(sIdx[i], eIdx[i] + 1):
                seen[cwnd[idx]] += cwnd[idx]
            loss[cwnd[eIdx[i]]] += 1

        # Calculate p
        p = sum(loss) / sum(seen)
        pcwnd = np.nan_to_num(loss / seen)
        # pcwnd = np.nan_to_num(loss / sum(seen))

        # Replace 0s with previous nearest non zero value
        nn = p
        for i in range(len(pcwnd)):
            if pcwnd[i] > 0:
                nn = pcwnd[i]
            else:
                pcwnd[i] = nn
        return [pcwnd, p, sIdx, eIdx]

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(e, fname, exc_tb.tb_lineno)


def findLossCubic(cwnd):
    try:
        # p-cwnd graph
        maxcwnd = max(cwnd) + 1
        loss, seen = np.zeros(maxcwnd), np.zeros(maxcwnd)

        # Two pointers to find start/end point of each trapezoid
        sIdx = []
        eIdx = []
        p, q = 0, 0
        sFlag = False

        while p < len(cwnd) and q < len(cwnd):
            if not sFlag:
                while p + 1 < len(cwnd) and (cwnd[p + 1] - cwnd[p]) != 1:
                    p += 1
                if p + 1 == len(cwnd):
                    break
                else:
                    # todo: check if previous loss is false positive
                    if len(eIdx) and (cwnd[p] - cwnd[eIdx[-1]] >= -1):
                        eIdx.pop()
                    else:
                        sIdx.append(p)
                    sFlag = True
                    q = p + 1
                    continue
            else:
                while q + 2 < len(cwnd) and (cwnd[q] < cwnd[q + 1] or  # proceed if 1) increasing
                                             cwnd[q] - cwnd[q - 1] > 2 and cwnd[q] - cwnd[q + 1] > 2 or  # up spike
                                             cwnd[q] - cwnd[q + 1] > 0 and cwnd[q + 2] - cwnd[q + 1] > 0):  # down spike
                    q += 1
                if q + 2 == len(cwnd):
                    break
                else:
                    # todo: check if we should ignore this trapezoid
                    if len(sIdx) and q - sIdx[-1] < 3:
                        sIdx.pop()
                    else:
                        eIdx.append(q)
                    sFlag = False
                    p = q + 1

        if len(sIdx) != len(eIdx):
            sIdx.pop()

        # todo: check this
        for i in range(len(eIdx)):
            for idx in range(sIdx[i], eIdx[i] + 1):
                seen[cwnd[idx]] += cwnd[idx]
            loss[cwnd[eIdx[i]]] += 1

        # Calculate p
        pcwnd = np.nan_to_num(loss / seen)
        # pcwnd = np.nan_to_num(loss / sum(seen))

        # Replace 0s with previous nearest non zero value
        nn = max(pcwnd)
        for i in range(len(pcwnd)):
            if pcwnd[i] > 0:
                nn = pcwnd[i]
            else:
                pcwnd[i] = nn

        return [pcwnd, sIdx, eIdx]

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(e, fname, exc_tb.tb_lineno)
