# btc_feasability

btc_feasability


## Requirements

* Python
	* If you are on a Mac, python is pre-installed
		* Open up a terminal and run:
		* `sudo apt install python python-dev` 
		* `git clone https://github.com/tylerGoulding/btc_feasability.git`
		*  `cd btc_feasability`
		* `pip install requirements.txt`
	* If you are on a Linux, run the following:
		* Open up a terminal and run:
		* `sudo apt install python python-dev` 
		* `git clone https://github.com/tylerGoulding/btc_feasability.git`
		*  `cd btc_feasability`
		* `pip install requirements.txt`
	* If you are on a Windows, IDK, I'll figure that out later.

## Usage

The model is written in Python. The model accepts two command line parameters. One is a required config file that follows the format of the sample.config file. The other is an output file to write the calculated values to an excel format.
To run the program, open up a terminal and run: 
`./bitcoin_main.py --config sample.config -o btc_output.xlsx`

## Config File
The config file is formatted in the following way and is parsed in a JSON format. As a result, comments are not allow inside the file itself so a copy is proved below with comments inlined.

```
{

    "verbose": false,        # sets output to verbose mode   
    "cost_per_kWh": 0.03,    # Expected costs per kWh


	# The model supports both exp growth and linear 
	# growth of the total network hashrate. 
	# As such, you can change the growth type to 
	# either "linear" or "exp"
    "btc_growth": "linear",      
    "btc_linear_slope": 5000,  # If linear, this is the slope
    "btc_log_slope": 9E9,      # If exp, this is the constant
    "btc_pool_hash": 56611000, # Base hashrate of the Pool
    "btc_pool_fee": 0.01,      # 1% == .01
    "btc_avg_transaction_fee": 0.415,   #base average transaction fee
    "btc_transaction_fee_growth": 0.0005,   #I assume tansaction fee grows linear with time, this sets that constant


    # "init_invest" is the current net profit of the opperation.
    # So if you have zero miners and are just starting this should be 0.
    # However, if you have X miners that cost Y initially, BUT you have made recoved Y in your net profits, 
    #     this should also be zero.
    "init_invest": 0,    
    "total_miners": 24, # currently how many active miners do you have
    
    # This is if you are using the excess heat to offset the cost of gas...  1 == January, 11 == November.
    "months_with_free_electric": [1,2,3,11,12]

}
```