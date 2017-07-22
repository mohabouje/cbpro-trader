#
# engine.py
# Mike Cardillo
#
# Subsystem containing all trading logic and execution
import time
import gdax
from decimal import *


#class OrderBookNoRestart(gdax.OrderBook):
#    def on_error(self, e):
#        print e


class TradeEngine():
    def __init__(self, auth_client):
        self.auth_client = auth_client
        self.order_book = gdax.OrderBook()
        self.usd = self.get_usd()
        self.btc = self.get_btc()
        self.last_balance_update = time.time()
        self.order_book.start()
        time.sleep(10)
        self.last_balance_update = time.time()

    def get_usd(self):
        try:
            for account in self.auth_client.get_accounts():
                if account.get('currency') == 'USD':
                    return self.round_usd(account.get('available'))
        except AttributeError:
            return self.round_usd('0.0')

    def get_btc(self):
        try:
            for account in self.auth_client.get_accounts():
                if account.get('currency') == 'BTC':
                    return self.round_btc(account.get('available'))
            return self.round_btc(self.auth_client.get_accounts()[0]['available'])
        except AttributeError:
            return self.round_btc('0.0')

    def round_usd(self, money):
        return Decimal(money).quantize(Decimal('.01'), rounding=ROUND_DOWN)

    def round_btc(self, money):
        return Decimal(money).quantize(Decimal('.00000001'), rounding=ROUND_DOWN)

    def update_amounts(self):
        if time.time() - self.last_balance_update > 10.0:
            self.btc = self.get_btc()
            self.usd = self.get_usd()
            self.last_balance_update = time.time()

    def print_amounts(self):
        print "[BALANCES] USD: %.2f BTC: %.8f" % (self.usd, self.btc)

    def place_buy(self):
        amount = self.get_usd()
        bid = self.order_book.get_ask() - Decimal('0.01')
        amount = self.round_btc(Decimal(amount) / Decimal(bid))

        if amount > Decimal('0.01'):
            return self.auth_client.buy(type='limit', size=str(amount),
                                        price=str(bid), post_only=True,
                                        product_id='BTC-USD')
        else:
            ret = {'status': 'done'}
            return ret


    def buy(self, amount=None):
        ret = self.place_buy()
        bid = ret.get('price')
        while ret.get('status') != 'done':
            if ret.get('status') == 'rejected':
                ret = self.place_buy()
                bid = ret.get('price')
            elif Decimal(bid) < self.order_book.get_ask() - Decimal('0.01'):
                if ret.get('id'):
                    self.auth_client.cancel_order(ret.get('id'))
                while self.get_usd() == Decimal('0.0') and ret.get('status') != 'done':
                    time.sleep(1)
                    if ret.get('id'):
                        ret = self.auth_client.get_order(ret.get('id'))
                if ret.get('status') != 'done':
                    ret = self.place_buy()
                    bid = ret.get('price')
            if ret.get('id'):
                ret = self.auth_client.get_order(ret.get('id'))

    def place_sell(self):
        amount = self.get_btc()
        ask = self.order_book.get_bid() + Decimal('0.01')

        if amount > Decimal('0.01'):
            return self.auth_client.sell(type='limit', size=str(amount),
                                         price=str(ask), post_only=True,
                                         product_id='BTC-USD')
        else:
            ret = {'status': 'done'}
            return ret

    def sell(self, amount=None):
        ret = self.place_sell()
        ask = ret.get('price')
        while ret.get('status') != 'done':
            if ret.get('status') == 'rejected':
                ret = self.place_sell()
                ask = ret.get('price')
            elif Decimal(ask) > self.order_book.get_bid() + Decimal('0.01'):
                if ret.get('id'):
                    self.auth_client.cancel_order(ret.get('id'))
                while self.get_btc() == Decimal('0.0') and ret.get('status') != 'done':
                    time.sleep(1)
                    if ret.get('id'):
                        ret = self.auth_client.get_order(ret.get('id'))
                if ret.get('status') != 'done':
                    ret = self.place_sell()
                    ask = ret.get('price')
            if ret.get('id'):
                ret = self.auth_client.get_order(ret.get('id'))

    def determine_trades(self, indicators, cur_period):
        self.update_amounts()
        if Decimal(indicators['vol_macd_hist']) > Decimal('-0.15'):
            if Decimal(indicators['macd_hist']) >= Decimal('0.2'):
                # buy btc
                if (self.get_usd() / self.order_book.get_bid()) >= Decimal('0.01'):
                    print "BUYING BTC!"
                    self.buy()
                    self.usd = self.get_usd()
            elif Decimal(indicators['macd_hist']) <= Decimal('-0.2'):
                # sell btc
                if self.get_btc() >= Decimal('0.01'):
                    print "SELLING BTC!"
                    self.sell()
                    self.btc = self.get_btc()
        self.print_amounts()