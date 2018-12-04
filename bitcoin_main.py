#!/usr/bin/env python
from btc_ops import *
import argparse 
import sys
import datetime
import json
from matplotlib.dates import MonthLocator,DayLocator, HourLocator, DateFormatter, drange
import numpy as np

from matplotlib.dates import date2num

import math

def buildDictFromFile(f):
    d = {}
    for line in f:
        key, value = line.strip.split(":")
        d[key] = value;
    return d;

def main():
    parser = argparse.ArgumentParser(description='Config file used to set the parameters of the model.')
    parser.add_argument("-c", "--config", type=argparse.FileType('r'),
                        default="")
    parser.add_argument("-o", "--outfile",
                    help="output file name", metavar="FILE",default="btc_model_{}.xlsx".format(datetime.datetime.now().strftime("%m_%d_%Y")))
    args = parser.parse_args()
    if (args.config == ""):
        print "Please provide a proper config file"
        return
    para = json.load(args.config)
    ScrubGrass = Operation(datetime.datetime.now(), 
                        para["init_invest"],  
                        para['total_miners'],
                        cost_per_kWh = para["cost_per_kWh"],
                        btc_growth = para["btc_growth"],
                        btc_exch_rate = para["btc_exch_rate"],
                        noEcost = para["months_with_free_electric"],
                        btc_linear_slope = para["btc_linear_slope"],
                        btc_log_slope = para["btc_log_slope"],
                        btc_pool_hash = para["btc_pool_hash"],
                        btc_pool_growth = para["btc_pool_growth"],

                        btc_pool_fee = para["btc_pool_fee"],
                        btc_avg_transaction_fee = para["btc_avg_transaction_fee"],
                        btc_transaction_fee_growth = para["btc_transaction_fee_growth"],
                        max_cap = 360, 
                        min_batch_order = 24, 
                        verbose = para['verbose'])
    ScrubGrass.daily_cost[-1]+=100000
    for i in xrange(1000):
        ScrubGrass.add_miner(Miner(13.2, 350, 1520,shipping = True))
    ScrubGrass.tick(365*4)
     # ScrubGrass.generateExcel(args.outfile)

    # plt.ion()

  ############################################################################
    #################  Plotting BTC related things #############################
    ############################################################################
    plt.style.use(['ggplot'])
    plt.xticks(rotation=60)

    fig, (a0, a1,a2,a3) = plt.subplots(4,1)

    plt.xticks(rotation=60)
    a0.xaxis.set_major_locator(MonthLocator())
    a0.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    a0.fmt_xdata = DateFormatter('%Y-%m')

    plt.xticks(rotation=60)
    a1.xaxis.set_major_locator(MonthLocator())
    a1.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    a1.fmt_xdata = DateFormatter('%Y-%m')

    # plt.xticks(rotation=60)
    a1.axes.get_xaxis().set_ticklabels([])
    a0.axes.get_xaxis().set_ticklabels([])

    fig.autofmt_xdate()

    plt.suptitle("Bitcoin-related Modeling")

    a0.plot(ScrubGrass.dates, ScrubGrass.btc_bs,'r')
    a0.set_ylabel("Block Size")

    a1.plot(ScrubGrass.dates, ScrubGrass.btc_HR,'b')
    a1.set_ylabel("Total Hashrate (TH/s)")

    a2.plot(ScrubGrass.dates, ScrubGrass.btc_exc,'g')
    a2.set_ylabel("Exchange Rate (USD)")
    a3.plot(ScrubGrass.dates, ScrubGrass.btc_transFee)
    a3.set_ylabel("Transaction Fee")
    # ax.legend()

    ############################################################################
    ############################################################################
    ############################################################################


    ############################################################################
    ###############  Plotting Money related things #############################
    ############################################################################
    plt.style.use(['ggplot'])
    fig, ax = plt.subplots()
    plt.xticks(rotation=60)

    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    ax.fmt_xdata = DateFormatter('%Y-%m')
    fig.autofmt_xdate()

    plt.title("Monetary Returns as a function of Time")
    plt.xlabel("Date")
    plt.ylabel("USD")

    plt.plot(ScrubGrass.dates, ScrubGrass.get_cum_sum('revenue'), 'g-', linewidth=2)
    plt.plot(ScrubGrass.dates, -ScrubGrass.get_cum_sum('cost'), 'r-', linewidth=2)
    plt.plot(ScrubGrass.dates, ScrubGrass.get_cum_sum('net'), 'b-', linewidth=2)
    ############################################################################
    ############################################################################
    ############################################################################



    ############################################################################
    ###############  Plotting Money related things #############################
    ############################################################################
    fig, ax = plt.subplots()
    ax.xaxis.set_major_locator(MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    ax.fmt_xdata = DateFormatter('%Y-%m')
    fig.autofmt_xdate()

    plt.suptitle("Monetary Returns as a function of Time (Split)")
    plt.subplot(311)
    plt.xlabel("Date")
    plt.ylabel("USD")
    plt.plot(ScrubGrass.dates,ScrubGrass.get_cum_sum('revenue'),'g-')

    plt.subplot(312)
    plt.xlabel("Date")
    plt.ylabel("USD")
    plt.plot(ScrubGrass.dates,ScrubGrass.get_cum_sum('cost'),'r-')

    plt.subplot(313)
    plt.xlabel("Date")
    plt.ylabel("USD")
    plt.plot(ScrubGrass.dates,ScrubGrass.get_cum_sum('net'),'b-')
    ############################################################################
    ############################################################################
    ############################################################################


    ############################################################################
    ###############  Plotting Money related things #############################
    ############################################################################
    fig, ax_dpm = plt.subplots()
    plt.xticks(rotation=60)

    ax_dpm.xaxis.set_major_locator(MonthLocator(interval=4))
    ax_dpm.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    ax_dpm.fmt_xdata = DateFormatter('%Y-%m')
    # plt.locator_params(axis='x', nbins=12)

    fig.autofmt_xdate()

    ax_dpm.set_title("Daily Per miner returns")
    ax_dpm.set_xlabel("Date")
    ax_dpm.set_ylabel("USD")
    ax_dpm.plot(ScrubGrass.dates, ScrubGrass.daily_per_miner_rev, 'g-', linewidth=1, label="Revenue")
    ax_dpm.plot(ScrubGrass.dates, -np.array(ScrubGrass.daily_per_miner_cost), 'r-', linewidth=1, label="Cost")
    ax_dpm.plot(ScrubGrass.dates, ScrubGrass.daily_per_miner_net, 'b-', linewidth=1, label="Net")
    ax_dpm.legend()
    ############################################################################
    ############################################################################
    ############################################################################

    f, (a0, a1) = plt.subplots(2,1, gridspec_kw = {'height_ratios':[2, 3]})
    # plt.subplot(211)
    plt.xticks(rotation=60)
    # plt.ylabel("Cummulative Revenue")
    ax.xaxis.set_major_locator(MonthLocator())
    # ax.xaxis.set_minor_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))

    ax.fmt_xdata = DateFormatter('%Y-%m')
    fig.autofmt_xdate()


    mC = sorted(ScrubGrass.get_monthly_data('cost').items()) # sorted by key, return a list of tuples
    mR = sorted(ScrubGrass.get_monthly_data('revenue').items()) # sorted by key, return a list of tuples
    mN = sorted(ScrubGrass.get_monthly_data('net').items()) # sorted by key, return a list of tuples

    monthly_dates, mCosts = zip(*mC) # unpack a list of pairs into two tuples
    monthly_dates, mRev = zip(*mR) # unpack a list of pairs into two tuples
    monthly_dates, mNet = zip(*mN) # unpack a list of pairs into two tuples
    mNet_cumsum = np.array(mNet).cumsum(axis=0)
    mRev_cumsum = np.array(mRev).cumsum(axis=0)
    mCosts_cumsum = np.array(mCosts).cumsum(axis=0)
    # print mC
    # workbook = xlsxwriter.Workbook('monthly.xlsx')
    # worksheet = workbook.add_worksheet()
    # # print zip(mC,mR,mN);
    # row = 0
    # col = 0

    # for date,c,r,n,cc,rc,nc  in zip(monthly_dates,mCosts,mRev,mNet,mNet_cumsum,mRev_cumsum,mCosts_cumsum):
    #     row += 1
    #     worksheet.write(row, col, date.strftime('%x %X'))
    #     worksheet.write(row, col+1, c)
    #     worksheet.write(row, col+2, r)
    #     worksheet.write(row, col+3, n)
    #     worksheet.write(row, col+4, cc)
    #     worksheet.write(row, col+5, rc)
    #     worksheet.write(row, col+6, nc)
    # workbook.close()

    plt.suptitle("Monthly returns for entire Operation")


    monthly_dates_ = date2num(monthly_dates)

    # plt.subplot(211)
    a0.bar(monthly_dates_-8, -np.array(mCosts),width=8,color='r',align='center')
    a0.bar(monthly_dates_, np.array(mRev),width=8,color='g',align='center')
    a0.bar(monthly_dates_+8, np.array(mNet),width=8,color='b',align='center')
    a0.set_ylabel("USD")
    a1.set_ylabel("USD")

    a1.set_xlabel("Months")

    # plt.subplot(212)
    a0.axes.get_xaxis().set_ticklabels([])

    a1.bar(monthly_dates, -mCosts_cumsum,width=12,color='r',align='center')
    a1.bar(monthly_dates, mRev_cumsum,width=12,color='g',align='center')
    a1.bar(monthly_dates, mNet_cumsum,width=12,color='b',align='center')
    # a0.plot(ScrubGrass.dates,ScrubGrass.get_cum_sum('net'),'b-')

    fig, ax = plt.subplots()
    # plt.subplot(211)
    plt.xticks(rotation=60)

    plt.xlabel("Time")
    plt.ylabel("BTC Hashrate")
    ax.xaxis.set_major_locator(MonthLocator())
    # ax.xaxis.set_minor_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    ax.fmt_xdata = DateFormatter('%Y-%m')
    fig.autofmt_xdate()
    plt.plot(ScrubGrass.dates, ScrubGrass.btc_HR)


    fig, ax = plt.subplots()
    # plt.subplot(211)
    plt.xticks(rotation=60)

    plt.xlabel("Date")
    plt.ylabel("Total Miners")
    ax.xaxis.set_major_locator(MonthLocator())
    # ax.xaxis.set_minor_locator(DayLocator())
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))

    ax.fmt_xdata = DateFormatter('%Y-%m')
    fig.autofmt_xdate()
    plt.plot(ScrubGrass.dates, ScrubGrass.daily_active_miners, label='Active Miners')
    plt.plot(ScrubGrass.dates, ScrubGrass.num_miners, label='Total Miners')
    ax.legend()
    plt.show()


if __name__ == '__main__':
    main()