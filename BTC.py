import random
import numpy as np
import requests
import datetime

AVG_BLOCK_TIME = 10; # minutes
blocks_per_day = 24*60./AVG_BLOCK_TIME;

class BTC:
    """
    Bitcoin class that encompasses all that is bitcoin. 
        Maintains the current exchange rate and total hashrate of all miners in the
        world
    
    """
    halving_date = datetime.datetime(2020, 4, 22)
    
    def __init__(self, date, block_size=12.5, growth = 'linear', 
                       lin_slope = 50000,  log_slope = 9E9,
                       pool_hash =  1200,     pool_fee = 0, 
                       pool_growth = 0, ex_rate = 'latest',
                       ex_growth = 0,
                       trans_fee = 0,     trans_growth =0):
        self.BLOCK_SIZE = block_size
        self.base_transaction_fee = trans_fee #BTC
        self.transaction_fee = self.base_transaction_fee
        self.transaction_fee_growth = trans_growth
        self.pool_growth = pool_growth
        # hashrate changes so much, get the last week and average to get an idea
        try:
            hashrate_json = requests.get("https://api.blockchain.info/charts/hash-rate?timespan=1week&format=json",timeout = .1).json()
            sum_hash = 0.0
            for value in hashrate_json['values']:
                sum_hash += value['y']
            self.base_hashrate = sum_hash/len(hashrate_json['values'])
        except:
            self.base_hashrate = 50000000
        self.totalHashrate = self.base_hashrate


        # Grab the latest exchange
        if (ex_rate == 'latest'):
            try:
                exc_rate = requests.get('https://blockchain.info/ticker')
                # Turn the JSON into something useful
                self.base_exchange_rate = float(str(exc_rate.json()['USD']['last']))
            except:
                self.base_exchange_rate = 6000
        else:
            self.base_exchange_rate = ex_rate

        self.exchange_rate = self.base_exchange_rate
        self.base_slushpool_hash = pool_hash
        self.slushpool_hash = self.base_slushpool_hash
        self.pool_fee = pool_fee
        self.current_age = 0;
        self.current_date = date;
        self.growth = growth
        self.lin_slope = lin_slope
        self.log_slope = log_slope

    def age(self):
        """ Updates total hashrate as time progresses """
        self.current_age += 1;
        self.current_date += datetime.timedelta(days=1)

        price_noise = 0#np.random.normal(0,300,1)
        hash_noise = np.random.normal(0,5000000,1)

        # this assumes exchange rate is constant just with a lil noise
        self.exchange_rate = self.base_exchange_rate + price_noise + 0*self.current_age 
        self.transaction_fee = self.transaction_fee_growth*self.current_age + self.base_transaction_fee
        if (self.current_date >= BTC.halving_date):
            BTC.halving_date = BTC.halving_date + datetime.timedelta(days=1458.333)
            self.BLOCK_SIZE = self.BLOCK_SIZE/2.
        if (self.growth == 'linear'):
            self.slushpool_hash = self.base_slushpool_hash + self.pool_growth*self.current_age 
            self.totalHashrate = self.base_hashrate + self.lin_slope*self.current_age + hash_noise
        elif (self.growth == 'log'):
            self.totalHashrate = self.base_hashrate + self.log_slope*np.log(self.current_age) + hash_noise
        return self.exchange_rate, self.totalHashrate, self.BLOCK_SIZE, self.transaction_fee


    def get_daily_rev(self,hash_rate, r = 'usd'):
        """ Calculates the daily revenue for a givent hashrate and pool """
        p_success = self.slushpool_hash/self.totalHashrate
        pool_blocks = p_success * blocks_per_day
        coins_per_day = pool_blocks*(self.BLOCK_SIZE + self.transaction_fee)

        if r == 'usd':
            return (hash_rate/float(self.slushpool_hash))*coins_per_day*self.exchange_rate*(1.-self.pool_fee)
        return (hash_rate/float(self.slushpool_hash))*coins_per_day*(1-self.pool_fee)
