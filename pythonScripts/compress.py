# Combine adjacent tcpprobe entries with the same cwnd value

import os
import glob
import time
import pandas as pd
import numpy as np
import warnings
from multiprocessing import Pool

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


def compress(filename):
    try:
        print("Processing: " + filename)
        t0 = time.time()
        df = pd.read_csv(filename, header=None, delim_whitespace=True, usecols=[0, 4, 6, 9],
                         names=["time", "src", "dst", "length", "snd_nxt", "snd_una",
                                "cwnd", "ssthresh", "snd_wnd", "srtt", "rcv_wnd"])

        # Take unique values for 4 selected columns
        cwnd = df['cwnd'][:-1]
        idx = np.insert(np.diff(cwnd).astype(bool), 0, True)

        timestamp = df['time'].iloc[idx].round(6)
        sndnxt = df['snd_nxt'].iloc[idx].apply(int, base=16)
        cwnd = df['cwnd'].iloc[idx]
        srtt = df['srtt'].iloc[idx]

        df = pd.concat([timestamp, sndnxt, cwnd, srtt], axis=1)

        dstFolder = "/mnt/ssd/sigm19data/" + '/'.join(filename.split('/')[-2: -1])
        if not os.path.exists(dstFolder):
            os.makedirs(dstFolder)

        dstFile = dstFolder + '/' + filename.split('/')[-1]
        df.to_csv(dstFile, sep=",", index=False)
        t2 = time.time()

        print(filename + " -- Elapse time: " + str(t2 - t0) + "s")

    except Exception as e:
        print(filename + str(e))


if __name__ == "__main__":
    srcFolder = "/media/yi/hdisk/tcpdata/sigm19_video/"
    filenames = []
    for f in glob.iglob(srcFolder + '*video*', recursive=False):
        filenames.append(f)
    print(filenames)
    with Pool(5) as p:
        p.map(compress, filenames)
