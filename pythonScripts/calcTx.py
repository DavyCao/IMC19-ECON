# Code for calculating throughput

from numba import jit
import numpy as np
import math
from scipy import stats


def calcTxReno(scwnd, rounds, pcwnd, p, rtt):
    # ECON
    [alpha, x] = renoHelper(scwnd, pcwnd, rounds)
    n = alpha + scwnd + (x - 1) - 1
    t = (x + 1) * rtt
    econ = n / t
    # print("reno -- scwnd = " + str(scwnd) + "; Alpha = " + str(alpha) + "; X: " + str(x) + "; rtt: " + str(rtt))

    b, minRTO = 1, 0.2

    # PFTK
    a1 = (1 - p) / p
    a2 = (2 + b) / (3 * b)
    a3 = (8 * (1 - p)) / (3 * b * p)
    a4 = (2 + b) / (3 * b)
    a5 = (2 + b) / 6
    a6 = 2 * b * (1 - p) / (3 * p)
    a7 = (2 + b) / 6
    pftk = (a1 + a2 + math.sqrt(a3 + a4 ** 2)) / (rtt * (a5 + math.sqrt(a6 + a7 ** 2) + 1))

    # PFTK-C
    b1 = a1
    b2 = a3
    b3 = (3 * b - 2) ** 2 / (9 * b ** 2)
    b4 = (3 * b - 2) / (3 * b)
    b5 = a6
    b6 = (3 * b - 2) ** 2 / 36
    b7 = (3 * b + 8) / 6
    pftkc = (b1 + math.sqrt(b2 + b3) - b4) / (rtt * (math.sqrt(b5 + b6) + b7))

    # PFTK-R
    rto = max(minRTO, 2 * rtt)
    ew = -1 + math.sqrt(8 / (3 * b * p) + 1)
    ea = rtt * (max(np.log2(ew / 2), 1) + b * (ew / 2 + 1) + 2) + rto
    pftkr = (1 / p + ew) / ea

    res = [econ, pftk, pftkc, pftkr, t, scwnd + (x - 1)]
    return np.array(res)


@jit
# History-based predictors
def calcTxHB(ewma, xputOB, lt, tt):
    # EWMA
    alpha, beta = 0.8, 0.8
    if ewma == 0:
        ewma = xputOB[-1]
    else:
        ewma = (1 - alpha) * ewma + alpha * xputOB[-1]

    # HW
    if lt == 0:
        lt = xputOB[-1]
        ft = ewma
    elif tt == 0:
        tt = xputOB[-1] - lt
        ft = ewma
    else:
        oldLt, oldTt = lt, tt
        lt = alpha * xputOB[-1] + (1 - alpha) * (oldLt + oldTt)
        tt = beta * (lt - oldLt) + (1 - beta) * oldTt
        ft = lt + tt

    # Last Sample
    ls = xputOB[-1]

    # Harmonic mean
    hm = stats.hmean(xputOB[-5:])

    # todo ARMA
    # ar =

    res = [ls, hm, ewma, ft, lt, tt]
    return res


# Calculate: alpha -> index of the first loss; x -> round of the first loss
@jit
def renoHelper(scwnd, pcwnd, rounds):
    alpha, index, pr = 0, 0, 1

    cwnd = scwnd
    if cwnd < len(pcwnd):
        _p = pcwnd[cwnd]
    else:
        _p = pcwnd[-1]

    for n in range(rounds):
        cwnd = scwnd + n
        for m in range(cwnd):
            if m == 0:
                if n != 0:
                    pr = pr / _p * (1 - _p)
                if cwnd < len(pcwnd):
                    _p = pcwnd[cwnd]
                else:
                    _p = pcwnd[-1]
                pr = pr * _p
            else:
                pr = pr * (1 - _p)
            index += 1
            alpha += index * pr

    x, rem, c = 0, alpha, scwnd
    while rem > 0:
        x += 1
        rem -= c
        c += 1

    res = [alpha, x]
    return res


def getCubicCwnd(t, scwnd):
    c, beta = 0.4, 0.3
    wmax = int(scwnd / (1 - beta))
    k = (wmax * beta / c) ** (1/3)
    cwnd = int(c * (t - k) ** 3 + wmax)
    return cwnd


@jit
def calcTxCubic(scwnd, rounds, pcwnd, rtt):
    c, beta = 0.4, 0.3
    wmax = int(scwnd / (1 - beta))
    k = (wmax * beta / c) ** (1/3)

    # Calculate the cwnd value for each round trip
    t, cwnds = 0, []
    for i in range(rounds):
        cwnd = int(c * (t - k) ** 3 + wmax)
        cwnds.append(cwnd)
        t += rtt

    # #pkts sent
    maxPktNum = sum(cwnds)

    # Calculate alpha and x
    idxW, cnt, alpha, pr = 0, 0, 0, 1
    cwnd = cwnds[idxW]
    if cwnd < len(pcwnd):
        _p = pcwnd[cwnd]
    else:
        _p = pcwnd[-1]

    for idxP in range(maxPktNum):
        # print(idxP)
        if idxP != 0:
            pr *= ((1 - _p) / _p)

        # See if need to update cwnd
        if cnt == cwnds[idxW]:
            cnt = 0
            idxW += 1
            cwnd = cwnds[idxW]
            if cwnd < len(pcwnd):
                _p = pcwnd[cwnd]
            else:
                _p = pcwnd[-1]

        cnt += 1
        pr *= _p
        alpha += (idxP + 1) * pr

    x, rem, idx = 0, alpha, -1
    while rem > 0:
        x += 1
        idx += 1
        rem -= cwnds[idx]

    n = alpha + cwnds[idx] - 1
    t = (x + 1) * rtt
    econ = n / t

    # print("cubic -- scwnd = " + str(scwnd) + "; Alpha = " + str(alpha) + "; X: " + str(x) + "; rtt:" + str(rtt))
    res = [econ, t, cwnds[idx]]
    return np.array(res)


def calcTxSS(rounds, pcwnd, rtt):
    icwnd = 10
    [alpha, x] = SSHelper(icwnd, pcwnd, rounds)
    n = alpha + icwnd * 2 ** (x - 1) - 1
    t = (x + 1) * rtt
    econ = n / t
    res = [econ, t, icwnd * 2 ** (x - 1)]
    return np.array(res)


@jit
def SSHelper(icwnd, pcwnd, rounds):
    alpha, index, pr = 0, 0, 1

    cwnd = icwnd
    if cwnd < len(pcwnd):
        _p = pcwnd[cwnd]
    else:
        _p = pcwnd[-1]

    for n in range(rounds):
        cwnd = icwnd * 2 ** n
        for m in range(cwnd):
            if m == 0:
                if n != 0:
                    pr = pr / _p * (1 - _p)
                if cwnd < len(pcwnd):
                    _p = pcwnd[cwnd]
                else:
                    _p = pcwnd[-1]
                pr = pr * _p
            else:
                pr = pr * (1 - _p)
            index += 1
            alpha += index * pr

    x = int(math.log2(alpha / icwnd)) + 1
    res = [alpha, x]
    return res
