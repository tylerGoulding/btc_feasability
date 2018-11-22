#!/usr/bin/env python
from btc_ops import *
import argparse 
import sys
import datetime
import json
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
                        noEcost = para["months_with_free_electric"],
                        btc_linear_slope = para["btc_linear_slope"],
                        btc_log_slope = para["btc_log_slope"],
                        btc_pool_hash = para["btc_pool_hash"],
                        btc_pool_fee = para["btc_pool_fee"],
                        btc_avg_transaction_fee = para["btc_avg_transaction_fee"],
                        btc_transaction_fee_growth = para["btc_transaction_fee_growth"],
                        max_cap = 360, 
                        min_batch_order = 24, 
                        verbose = para['verbose'])
    ScrubGrass.daily_cost[-1]+=100000
    for i in xrange(1000):
        ScrubGrass.add_miner(Miner(13.2, 350, 1520,shipping = True))
    ScrubGrass.tick(365*3)
    ScrubGrass.generateExcel(args.outfile)



if __name__ == '__main__':
    main()