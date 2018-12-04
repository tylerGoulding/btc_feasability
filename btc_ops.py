import random
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator,DayLocator, HourLocator, DateFormatter, drange
from collections import OrderedDict
import numpy as np
import requests
import datetime
from matplotlib.dates import date2num
import math
import xlsxwriter

# INclude our custom BTC model
from BTC import BTC


###
### Lets define some global macros that will be used to improve readability
###
DEAD = -1;
SHIPPING = -2;
ALIVE = -3;
FIRST_HALVING = datetime.datetime(2020, 4, 22)

###
### Now we need to define some variables that we will assume
###
SHIP_TIME = 14; # 2 weeks... duh
AVG_BLOCK_TIME = 10; # minutes
ONE_DAY = datetime.timedelta(days=1)

class Miner:
    """
    Miner class acts as a single miner.

    """
    def __str__(self):
        return "M {} TH/s; age: {}".format(self.hashrate, self.age)

    def __init__(self,hashrate, cost, power_consumption, shipping = False, age = 0):
        """Initializes a miner to the specified values.

        Args:
            hashrate (int): Expected hashrate of the device in TH/s. ex.) 13.2
            cost (int): Cost to purchase the miner. ex) 350.00
            power_consumption (int): consumption in kW. ex) 1520
            shipping (int, optional): set if the device is being shipped and
                not currently in posession.
            age (int, optional): if buying used, set the current/estimated age
                of the miner
        """
        random.seed()

        # Set some variable that define the type of the Miner
        self.hashrate = hashrate
        self.cost = cost
        self.power_consumption = power_consumption
        self.current_age = age;
        self.is_dead = False

        # These are set based off ordering a new miner (assumes ship time = SHIPTIME)
        self.shipping = shipping;
        if (shipping == True):
            self.days_till_arrival = SHIP_TIME;
        else:
            self.days_till_arrival = 0;

        # TODO: fix these magic numbers
        self.prob_of_failure =  0.0001
        self.destruction_rate = 0.000001


    def age(self):
        """ Ages the miner by 1 day, Increases failure probability

        Returns:
            State of miner, age of miner (or days till arrival in SHIPPING)
        """
        if (self.shipping == False):
            self.current_age += 1
            self.is_dead = self._is_dead(self.current_age)
            if (self.is_dead == True):
                return (DEAD, 0)
            return (ALIVE,self.age)
        else:
            self.days_till_arrival -= 1
            if (self.days_till_arrival == 0):
                self.shipping = False
                return (ALIVE, self.age)

            return (SHIPPING, self.days_till_arrival)
    def _is_dead(self,age):
        """ Checks if today is the age where the miner fails.

        Returns:
            True if miner dies, False otherwise.
        """
        return (random.random() < (self.prob_of_failure + age*self.destruction_rate) )


class Rig:
    def __str__(self):
        return "Rig [current_cap = {}; max_cap = {}; avg_age = {}]".format(self.current_capacity, self.capacity, sum([m.current_age for m in self.miners])/float(self.current_capacity))

    def __init__(self,capacity, replacement_policy = 'immediate', populate_with_miner = False, miners = [], fill = False,fill_count = 0):
        self.capacity = capacity
        self.current_capacity = 0
        self.miners = []
        self.replacement_miners = 0
        if (populate_with_miner == True):
            if (fill == True):
                for i in xrange(min(fill_count,capacity)):
                    self.miners.append(Miner(13.2, 350, 1520))
                    self.current_capacity += 1
            else:
                for i in xrange(min(capacity,len(miners))):
                    self.miners.append(miners[i])
                    self.current_capacity += 1

    def get_total_hashrate(self):
        tHash = 0;
        for m in self.miners:
            if (m.shipping == False):
                tHash +=m.hashrate 
        return tHash

    def is_full(self):
        return not (self.current_capacity < self.capacity);

    def add_miner(self,miner):
        if self.current_capacity < self.capacity:
            self.miners.append(miner)
            self.current_capacity +=1;
            return miner.cost;
        return -1;


    def tick(self,cost_per_kWh):
        daily_cost = 0
        replacement_miners = 0
        # Age all miners and figure out how many failed
        active_miners = []
        shipping_miners = []
        dead_miners = []
        for m in self.miners:
            status = m.age()[0]
            if (status == DEAD):
                # miner failed and needs to be replaced
                dead_miners.append(m)
                self.current_capacity -= 1
                replacement_miners += 1
            elif (status == ALIVE):
                active_miners.append(m)
            else:
                shipping_miners.append(m)

        self.miners = active_miners + shipping_miners

        # print active_miners     
        total_power_consumption = (sum([m.power_consumption for m in active_miners]))
        daily_electric_cost = (total_power_consumption/1000.)*24*cost_per_kWh

        return replacement_miners, daily_electric_cost, len(active_miners)




class Operation:
    def __str__(self):
        return "Operation [Rigs = {}; Miners = {}]".format(len(self.rigs), sum([(r.current_capacity)for r in self.rigs]))

    def __init__(self, start_date, initial_investment, total_miners, 
                cost_per_kWh = .03,
                noEcost = [],
                btc_growth = "linear",
                btc_linear_slope = 50000,
                btc_log_slope = 9E9,
                btc_pool_hash = 56611000,
                btc_pool_fee = 0.01,
                btc_pool_growth = 1200, #1200
                btc_exch_rate = 'latest',
                btc_exch_growth = 10,
                btc_avg_transaction_fee = 0.415,
                btc_transaction_fee_growth = 0.0005,
                max_cap = 360, min_batch_order = 24, 
                replacement_policy = 'immediate', growth = 'aggresive', stop = 1000, verbose = False):
        self.verbose = verbose;
        self.cost_per_kWh = cost_per_kWh
        self.noEcost = noEcost
        self.min_batch_order = min_batch_order;
        self.max_cap = max_cap;
        self.date = start_date
        self.dates = [start_date]
        self.bitcoin = BTC(start_date, growth = btc_growth, lin_slope=btc_linear_slope, pool_hash = btc_pool_hash,
                            pool_fee = btc_pool_fee, pool_growth = btc_pool_growth,
                            ex_rate = btc_exch_rate,
                            trans_fee = btc_avg_transaction_fee,
                            trans_growth = btc_transaction_fee_growth)
        self.btc_exc = [self.bitcoin.exchange_rate]
        self.btc_HR = [self.bitcoin.totalHashrate]
        self.btc_bs = [self.bitcoin.BLOCK_SIZE]
        self.btc_transFee = [self.bitcoin.transaction_fee]
        self.replacement_policy = replacement_policy
        self.num_to_replace = 0
        self.daily_active_miners = [total_miners]

        # initialize some arrays for the mulla
        self.initial_investment = initial_investment
        self.daily_cost = [initial_investment]
        self.monthly_cost = {}

        self.cost = [initial_investment]
        self.daily_revenue = [0]
        self.monthly_revenue = {}

        self.revenue = [0]
        self.daily_net = [self.revenue[0]-self.cost[0]]
        self.monthly_net = {}

        self.daily_per_miner_rev = [0]
        self.daily_per_miner_cost = [0]
        self.daily_per_miner_net = [0]

        self.net = 0
        #initialize some arrays for fun:
        self.num_miners = [total_miners];
        self.daily_dead_miners = [0];
        self.rigs = []
        self.is_pooling = True;
        print "here"
        while (total_miners > 0):
            cap = 24
            self.rigs.append(Rig(cap, populate_with_miner = True, fill = True, fill_count = total_miners))
            total_miners -= cap;

    def add_miner(self,miner):
        for r in self.rigs:
            if (not r.is_full()):
                c = r.add_miner(miner);
                self.daily_cost[-1] += miner.cost
                key = datetime.datetime(self.date.year,self.date.month,1);
                self._add_to_dict(self.monthly_cost, key, miner.cost);
                self._add_to_dict(self.monthly_net, key, -miner.cost);
                return miner.cost;

        self.add_rig([miner]);
        new_cost = 5000.00 + miner.cost
        self.daily_cost[-1] += new_cost
        key = datetime.datetime(self.date.year,self.date.month,1);
        self._add_to_dict(self.monthly_cost, key, new_cost);
        self._add_to_dict(self.monthly_net, key, -new_cost);

        return 5000.00+miner.cost;

    def get_number_of_miners(self):
        tMiners = 0
        for r in self.rigs:
            tMiners +=r.current_capacity
        return tMiners

    def add_rig(self,miners):
        self.rigs.append(Rig(24, populate_with_miner = True, miners = miners))

    def get_cum_sum(self,d = "cost"):
        if (d == 'cost'):
            return np.array(self.daily_cost).cumsum(axis=0)
        elif (d == 'revenue'):
            return np.array(self.daily_revenue).cumsum(axis=0)
        elif (d == 'net'):
            return np.array(self.daily_revenue).cumsum(axis=0) \
                   - np.array(self.daily_cost).cumsum(axis=0)

    def get_monthly_data(self,t = "cost"):
        d = OrderedDict();
        if (t == 'cost'):
            print len(self.daily_cost)
            print len(self.dates)
            for i in xrange(len(self.daily_cost)):
                ddate = self.dates[i] 
                value = self.daily_cost[i]
                key = datetime.datetime(ddate.year,ddate.month,1);
                self._add_to_dict(d, key, value)
            return d
        if (t == 'revenue'):
            for ddate,value in zip(self.dates,self.daily_revenue):
                key = datetime.datetime(ddate.year,ddate.month,1);
                self._add_to_dict(d, key, value)
            return d
        if (t == 'net'):
            for ddate,rev_val,cost_val in zip(self.dates,self.daily_revenue,self.daily_cost):
                key = datetime.datetime(ddate.year,ddate.month,1);
                self._add_to_dict(d, key, rev_val)
                self._add_to_dict(d, key, -cost_val)
            return d
    def tick(self,time_frame):
        #replace this with a settable s:
        min_batch_replace_size = 12;

        # iterate through each day.
        for day in xrange(time_frame):
            self.date += ONE_DAY 
            self.dates.append(self.date)
            self.daily_cost.append(0);

            dailyExc, dailyHash, daily_block_size,t_fee = self.bitcoin.age()
            self.btc_transFee.append(t_fee)
            self.btc_exc.append(dailyExc)
            self.btc_HR.append(dailyHash)
            self.btc_bs.append(daily_block_size)

            daily_total_hashrate = 0
            daily_electric_cost = 0
            daily_dead_miners = 0
            daily_hardware_costs = 0
            daily_active_miners = 0

            if ((self.date < FIRST_HALVING) or (self.date.month in self.noEcost)):
                for r in self.rigs:
                    kwhCost = self.cost_per_kWh
                    if (self.date.month in self.noEcost):
                        kwhCost = 0.0
                    rig_dead_miners, rig_E_consume, rig_Workers = r.tick(kwhCost)

                    daily_dead_miners += rig_dead_miners
                    daily_electric_cost += rig_E_consume
                    daily_active_miners += rig_Workers
                    daily_total_hashrate += r.get_total_hashrate()

                if (self.replacement_policy == 'immediate'):
                    for i in xrange(0,daily_dead_miners):
                        new_miner = Miner(13.2, 350, 1520,shipping = True)
                        self.add_miner(new_miner)
            self.daily_active_miners.append(daily_active_miners)
            self.daily_dead_miners.append(daily_dead_miners)
            self.num_miners.append(self.get_number_of_miners())

            # print "daily_electric_cost: ", daily_electric_cost
            self.daily_cost[-1] += (daily_electric_cost)
            self.daily_revenue.append(self.bitcoin.get_daily_rev(daily_total_hashrate))

            self.daily_net.append(self.daily_revenue[-1]-self.daily_cost[-1]);
            if (self.daily_active_miners[-1] == 0):
                self.daily_per_miner_rev.append(0);
                self.daily_per_miner_cost.append(0)
                self.daily_per_miner_net.append(0)
            else:
                self.daily_per_miner_rev.append(self.daily_revenue[-1]/self.daily_active_miners[-1])
                self.daily_per_miner_cost.append(daily_electric_cost/self.daily_active_miners[-1])
                self.daily_per_miner_net.append((self.daily_revenue[-1]-daily_electric_cost)/self.daily_active_miners[-1])

            print self.daily_per_miner_cost[-1]
            self.net = self.get_cum_sum(d = "net")[-1]

            key = datetime.datetime(self.date.year,self.date.month,1)
            self._add_to_dict(self.monthly_cost, key, self.daily_cost[-1]);
            self._add_to_dict(self.monthly_revenue, key, self.daily_revenue[-1]);
            self._add_to_dict(self.monthly_net, key, self.daily_net[-1]);

            if self.verbose:
                print "_____________Day: {}____________________".format(self.date)
                print "Active Miners:", daily_active_miners
                print "perMiner revenue =", self.daily_revenue[-1]/self.daily_active_miners[-1]
                print "perMiner net =", self.daily_net[-1]/self.daily_active_miners[-1]

                print "daily dead =", daily_dead_miners            
                print "total hashrate =", daily_total_hashrate
    def generateExcel(self,fileName):

        workbook = xlsxwriter.Workbook(fileName)
        bold = workbook.add_format({'bold': True})
        neg_format = workbook.add_format({'font_color': 'red'})
        pos_format = workbook.add_format({'font_color': 'green'})
        worksheet = workbook.add_worksheet()
        worksheet.name = 'Parameters'
        worksheet.write(0, 0, "This is an auto-generated XLSX file. The values in this file were created using the model created by Tyler Goulding for ScrubGrass")
        worksheet.write(1, 0, "I am not a profession nor an expert in Bitcoin. These values reflect the parameters to the model and in no way predict the future performance of Bitcoin")

        row = 3
        col = 1
        worksheet.write(row, col, "Cost per KWh")
        worksheet.write(row, col+1, self.cost_per_kWh)

        worksheet = workbook.add_worksheet()
        worksheet.name = 'BTC'

        row = 0
        col = 0
        worksheet.write(row, col, "Date", bold)
        worksheet.write(row, col+2, "BlockSize", bold)
        worksheet.write(row, col+3, "Total Network Hashrate", bold)
        worksheet.write(row, col+4, "Exchange Rate", bold)
        worksheet.write(row, col+5, "Transaction Fee", bold)

        for date,bSize,hRate,eRate,tFee in zip(self.dates, self.btc_bs, 
                                self.btc_HR, self.btc_exc, self.btc_transFee):
            row += 1
            worksheet.write(row, col, date.strftime('%x %X'))
            worksheet.write_datetime(row, col+1, date)
            worksheet.write_number(row, col+2, bSize)
            worksheet.write_number(row, col+3, hRate)
            worksheet.write_number(row, col+4, eRate)
            worksheet.write_number(row, col+5, tFee)

        mC = sorted(self.get_monthly_data('cost').items()) # sorted by key, return a list of tuples
        mR = sorted(self.get_monthly_data('revenue').items()) # sorted by key, return a list of tuples
        mN = sorted(self.get_monthly_data('net').items()) # sorted by key, return a list of tuples

        monthly_dates, mCosts = zip(*mC) # unpack a list of pairs into two tuples
        monthly_dates, mRev = zip(*mR) # unpack a list of pairs into two tuples
        monthly_dates, mNet = zip(*mN) # unpack a list of pairs into two tuples
        mNet_cumsum = np.array(mNet).cumsum(axis=0)
        mRev_cumsum = np.array(mRev).cumsum(axis=0)
        mCosts_cumsum = np.array(mCosts).cumsum(axis=0)
        worksheet = workbook.add_worksheet()
        worksheet.name = "Monthly"

        # # print zip(mC,mR,mN);
        row = 0
        col = 0
        worksheet.write(row, col, "Month", bold)
        worksheet.write(row, col+2, "Revenue", bold)
        worksheet.write(row, col+3, "Cost", bold)
        worksheet.write(row, col+4, "Net Profit", bold)
        worksheet.write(row, col+5, "Cummulative Revenue", bold)
        worksheet.write(row, col+6, "Cummulative Cost", bold)
        worksheet.write(row, col+7, "Cummulative Net", bold)

        for date,r,c,n,cr,cc,cn  in zip(monthly_dates,mRev,mCosts,mNet,mRev_cumsum,mCosts_cumsum,mNet_cumsum):
            row += 1
            worksheet.write(row, col, date.strftime('%m/%d/%Y'))
            worksheet.write(row, col+2, r)
            worksheet.write(row, col+3, c)
            if (n>0):
                worksheet.write(row, col+4, n, pos_format)
            else:
                worksheet.write(row, col+4, n, neg_format)
            worksheet.write(row, col+5, cr)
            worksheet.write(row, col+6, cc)
            if (cn>0):
                worksheet.write(row, col+7, cn, pos_format)
            else:
                worksheet.write(row, col+7, cn, neg_format)

        workbook.close()
    def setup_plot(self):
        plt.ion()


    @staticmethod
    def _add_to_dict(d, key, value):
        d[key] = d.get(key, 0.0) + value




def main():
    ScrubGrass = Operation(datetime.datetime.now(), 0,  24,btc_exch_rate = 6000, max_cap = 360, min_batch_order = 24, verbose = False)
    # progress 4 days just to get us to a pretty date.
    ScrubGrass.tick(1)

    # Order 24 miners because why not?
    ScrubGrass.daily_cost[-1]+=100000
    for i in xrange(1000):
        ScrubGrass.add_miner(Miner(13.2, 350, 1520,shipping = True))
    ScrubGrass.tick(15)
    print ScrubGrass.date;
    ScrubGrass.tick(31)
    print ScrubGrass.date;
    ScrubGrass.tick(31)
    print ScrubGrass.date;
    ScrubGrass.tick(28)
    # for i in xrange(48):
    #     ScrubGrass.add_miner(Miner(13.2, 350, 1520,shipping = True))

    ScrubGrass.tick(31)
    print ScrubGrass.date;

    ScrubGrass.tick(30)
    print ScrubGrass.date;
    # for i in xrange(48):
    #     ScrubGrass.add_miner(Miner(13.2, 350, 1520,shipping = True))

    ScrubGrass.tick(31)

    ScrubGrass.tick(30)
    ScrubGrass.tick(31)
    ScrubGrass.tick(30)
    ScrubGrass.tick(31)
    ScrubGrass.tick(30)
    # for i in xrange(24):
        # ScrubGrass.add_miner(Miner(13.2, 350, 1520,shipping = True))
    # for i in xrange(122):
    #     ScrubGrass.add_miner(Miner(13.2, 350, 1520,shipping = True))

    ScrubGrass.tick(31)
    ScrubGrass.tick(30)
    ScrubGrass.tick(31)

    ScrubGrass.tick(365)
    ScrubGrass.tick(365)

    print ScrubGrass.date
    ScrubGrass.generateExcel("test.xlsx")
    # return
    plt.ion()

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

    f, (a0, a1) = plt.subplots(2,1, gridspec_kw = {'height_ratios':[3, 4]})
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
