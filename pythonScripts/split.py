# Extract only the time, sequence number, cwnd and rtt value columns from the tcpprobe log

import pandas as pd
import numpy as np
import os


def split():
    filenames = []
    dataFolder = "/media/yi/hdisk/tcpdata/cubic/sigm19Web_cubic/"
    for f in os.listdir(dataFolder):
        if "tcpprobe" in f:
            filenames.append(dataFolder + f)

    for filename in filenames:
        print(filename)

        tokens = filename.split('/')[-1].replace(".", "_").split("_")
        npc, runIndex = tokens[2], tokens[3]

        df = pd.read_csv(filename, header=None, delim_whitespace=True, usecols=[0, 1, 4, 6, 9],
                         names=["time", "src", "dst", "length", "snd_nxt", "snd_una",
                         "cwnd", "ssthresh", "snd_wnd", "srtt", "rcv_wnd"])

        src = df['src'].values
        ports = np.unique(src[0:100])

        for port in ports:

            print(port, len(df['time']))
            # Take the row data for each port
            idx = np.where(src == port)[0]
            timestamp = df['time'].iloc[idx]
            sndnxt = df['snd_nxt'].iloc[idx]
            cwnd = df['cwnd'].iloc[idx]
            srtt = df['srtt'].iloc[idx]

            # Take unique values for 4 selected columns
            cwnd = cwnd[:-1]
            idx = np.insert(np.diff(cwnd).astype(bool), 0, True)

            timestamp = timestamp.iloc[idx].round(6)
            sndnxt = sndnxt.iloc[idx].apply(int, base=16)
            cwnd = cwnd.iloc[idx]
            srtt = srtt.iloc[idx]

            dfOut = pd.concat([timestamp, sndnxt, cwnd, srtt], axis=1)

            dstFolder = "/mnt/ssd/sigm19data/" + '/'.join(filename.split('/')[-3: -1])
            if not os.path.exists(dstFolder):
                os.makedirs(dstFolder)

            dstFile = dstFolder + '/' + '_'.join(["data", npc, runIndex, port[-5:]]) + ".txt"
            dfOut.to_csv(dstFile, sep=",", index=False)


if __name__ == "__main__":
    split()
