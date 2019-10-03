# todo Plot the p-cwnd curve for each testbed -- connection and generate a webpage

from plotly import tools
import plotly.offline as of
import plotly.graph_objs as go
import numpy as np
import pandas as pd
from findLoss import findLossReno, findLossCubic
import datetime
import os
from multiprocessing import Pool


def pcwndPlotter(filename, t, cwnd, p, sIdx, eIdx):
    try:
        d_date = datetime.datetime.now()
        reg_format_date = d_date.strftime("%Y-%m-%d %I:%M:%S %p")

        # Use plotly to plot 1) tcpprobe trace (with scwnd/ecwnd); 2) p-cwnd
        xMin = min([cwnd[i] for i in eIdx])
        xMax = max([cwnd[i] for i in eIdx])
        trace = go.Scatter(
            x=t,
            y=cwnd,
            name='cwnd'
        )


        traceS = go.Scatter(
            x=t[sIdx],
            y=cwnd[sIdx],
            mode="markers",
            marker=dict(
                size=10,
                color='rgb(255, 0, 0)'
            ),
            name='CA Start Point'
        )

        traceE = go.Scatter(
            x=t[eIdx],
            y=cwnd[eIdx],
            mode="markers",
            marker=dict(
                size=10,
                color='rgb(0, 0, 0)'
            ),
            name='CA End Point'
        )

        traceP = go.Scatter(
            x=np.arange(xMin, xMax + 1),
            y=p[xMin:xMax + 1],
            name='Loss Rate'
        )

        # todo save the pcwnd data in csv format as well
        _p = np.vstack((np.arange(xMin, xMax + 1).astype(int), p[xMin:xMax + 1])).transpose()
        dfP = pd.DataFrame(_p, columns=['cwnd', 'p'])

        dfP.to_csv(os.path.join("/var/www/html/" + "/".join(filename.split("/")[4:]).split(".")[0] + ".csv"), sep=",")

        fig = tools.make_subplots(rows=2, cols=1, print_grid=False,
                                  subplot_titles=(
                                            # filename + " -- " + reg_format_date,
                                            "Congestion Evolution over Time",
                                            "Packetloss-cwnd Graph; Number of Losses: " + str(len(eIdx)))
                                  )
        fig.append_trace(trace, 1, 1)
        fig.append_trace(traceS, 1, 1)
        fig.append_trace(traceE, 1, 1)

        fig.append_trace(traceP, 2, 1)

        fig['layout']['xaxis1'].update(title='Time (s)')
        fig['layout']['yaxis1'].update(title='cwnd')
        fig['layout']['xaxis2'].update(title='cwnd')
        fig['layout']['yaxis2'].update(title='Loss Rate')
        # of.plot(fig, filename="/var/www/html/" + "/".join(filename.split("/")[4:]).split(".")[0] + ".html")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(e, fname, exc_tb.tb_lineno)


def run(filename):
    cc = filename.split('/')[4]

    # Read the data using pandas
    df = pd.read_csv(filename, header=0)
    timestamp = df['time'].values
    cwnd = df['cwnd'].values.astype(int)
    df = None

    if cc == "cubic":
        [pcwnd, sIdx, eIdx] = findLossCubic(cwnd=cwnd)
        print(filename + " -- " + str(len(eIdx)) + " -- " + str(min(eIdx)) + " -- " + str(max(eIdx)))
    else:
        [pcwnd, p, sIdx, eIdx] = findLossReno(cwnd=cwnd)
        print(filename + " -- " + str(len(eIdx)) + " -- " + str(min(eIdx)) + " -- " + str(max(eIdx)))

    pcwndPlotter(filename=filename, t=timestamp, cwnd=cwnd, p=pcwnd, sIdx=sIdx, eIdx=eIdx)


if __name__ == "__main__":
    dataFolders = [
        # "/mnt/ssd/sigm19data/reno/clemson_reno/",
        # "/mnt/ssd/sigm19data/reno/uw_reno/",
        # "/mnt/ssd/sigm19data/reno/lab_reno_sigm19/",
        # "/mnt/ssd/sigm19data/reno/azure_reno/",
        # "/mnt/ssd/sigm19data/reno/rutgers_reno/",
        #
        # "/mnt/ssd/sigm19data/cubic/clemson_cubic/",
        # "/mnt/ssd/sigm19data/cubic/korea_cubic/",
        # "/mnt/ssd/sigm19data/cubic/lab_cubic_sigm19/",
        # "/mnt/ssd/sigm19data/cubic/azure_cubic/",
        # "/mnt/ssd/sigm19data/cubic/rutgers_cubic/",
        #
        # "/mnt/ssd/sigm19data/reno/wireless_reno/",
        # "/mnt/ssd/sigm19data/cubic/wireless_cubic/",

        "/mnt/ssd/sigm19data/cubic/sigm19Web_cubic/",

        # "/mnt/ssd/sigm19data/reno/netchange_reno/",
    ]

    for dataFolder in dataFolders:
        cc = dataFolder.split('/')[-3]

        filenames = []
        for f in os.listdir(dataFolder):
            if "data_" in f:
                filenames.append(dataFolder + f)
        print(filenames)

        with Pool(20) as p:
            res = p.map(run, filenames)
