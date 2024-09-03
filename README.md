# Forex Backtesting System and Real-Time Algorithmic Trading Bot
## Introduction
This is a backtesting system and live trading bot, retrieving data from and booking orders into OANDA as an exchange.
New exchanges can be implemented in the future.

For now, only candle data and two indicators based on this data (Moving Average Crossover and Inside Bar Momentum) are implemented.
This codebase is capable of performing backtesting on historical data from any given period, generate trades and evaluate the trades based on the following metrics:
- Return on Investment
- Sharpe Ratio
- Profit to Drawdown ratio
- Total Time in Market

New metrics can also be implemented in the future. For the Sharpe ratio, the risk-free return is retrieved from a separate third-party API.

## Development
### Set-up
To set up the project, follow the following steps:
1. Clone the repository.
2. Run `pip install -r requirements.txt`
3. 

### Running backtesting locally
The backtesting system has its entry point in `backtesting_main.py`.
To run this, run `python3 backtesting_main.py`.
To change the currencies, properties or indicators, edit this file.

### Running the real-time trading bot locally
The real-time trading bot has its entry point in `real_time_trading_main.py`.
This system depends on a messaging queue, RabbitMQ, to run. To run this, follow these steps:
1. Install RabbitMQ. Follow the instructions on [this page](https://www.rabbitmq.com/docs/download).If on MacOS, you 
   If on MacOS, you can run `brew install rabbitmq` to install this.
2. Start the message queue broker by running `rabbitmq-server`.
3. Then run `python3 real_time_trading_main.py` to start the services.

Once again, you can edit this file to change the properties of how this bot will run.