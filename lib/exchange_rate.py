from datetime import datetime
import inspect
import requests
import sys
from threading import Thread
import time
import traceback
import csv
from decimal import Decimal

from electrum_twist.twist import COIN
from electrum_twist.plugins import BasePlugin, hook
from electrum_twist.i18n import _
from electrum_twist.util import PrintError, ThreadJob
from electrum_twist.util import format_satoshis


# See https://en.wikipedia.org/wiki/ISO_4217
CCY_PRECISIONS = {'BHD': 3, 'BIF': 0, 'BYR': 0, 'CLF': 4, 'CLP': 0,
                  'CVE': 0, 'DJF': 0, 'GNF': 0, 'IQD': 3, 'ISK': 0,
                  'JOD': 3, 'JPY': 0, 'KMF': 0, 'KRW': 0, 'KWD': 3,
                  'LYD': 3, 'MGA': 1, 'MRO': 1, 'OMR': 3, 'PYG': 0,
                  'RWF': 0, 'TND': 3, 'UGX': 0, 'UYI': 0, 'VND': 0,
                  'VUV': 0, 'XAF': 0, 'XAU': 4, 'XOF': 0, 'XPF': 0}

class ExchangeBase(PrintError):

    def __init__(self, on_quotes, on_history):
        self.history = {}
        self.quotes = {}
        self.on_quotes = on_quotes
        self.on_history = on_history

    def protocol(self):
        return "https"

    def get_json(self, site, get_string):
        url = "".join([self.protocol(), '://', site, get_string])
        response = requests.request('GET', url,
                                    headers={'User-Agent' : 'Electrum'})
        return response.json()

    def get_csv(self, site, get_string):
        url = "".join([self.protocol(), '://', site, get_string])
        response = requests.request('GET', url,
                                    headers={'User-Agent' : 'Electrum'})
        reader = csv.DictReader(response.content.split('\n'))
        return list(reader)

    def name(self):
        return self.__class__.__name__

    def update_safe(self, ccy):
        try:
            self.print_error("getting fx quotes for", ccy)
            self.quotes = self.get_rates(ccy)
            self.print_error("received fx quotes")
        except BaseException as e:
            self.print_error("failed fx quotes:", e)
        self.on_quotes()

    def update(self, ccy):
        t = Thread(target=self.update_safe, args=(ccy,))
        t.setDaemon(True)
        t.start()

    def get_historical_rates_safe(self, ccy):
        try:
            self.print_error("requesting fx history for", ccy)
            self.history[ccy] = self.historical_rates(ccy)
            self.print_error("received fx history for", ccy)
            self.on_history()
        except BaseException as e:
            self.print_error("failed fx history:", e)

    def get_historical_rates(self, ccy):
        result = self.history.get(ccy)
        if not result and ccy in self.history_ccys():
            t = Thread(target=self.get_historical_rates_safe, args=(ccy,))
            t.setDaemon(True)
            t.start()
        return result

    def history_ccys(self):
        return []

    def historical_rate(self, ccy, d_t):
        return self.history.get(ccy, {}).get(d_t.strftime('%Y-%m-%d'))


class Bit2C(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('api.bitcoinaverage.com', '/ticker/global/all')
        return dict([(r, Decimal(json[r]['last']))
                     for r in json if r != 'timestamp'])

    def history_ccys(self):
        return ['AUD', 'BRL', 'CAD', 'CHF', 'CNY', 'EUR', 'GBP', 'IDR', 'ILS',
                'MXN', 'NOK', 'NZD', 'PLN', 'RON', 'RUB', 'SEK', 'SGD', 'USD',
                'ZAR']

    def historical_rates(self, ccy):
        history = self.get_csv('api.bitcoinaverage.com',
                               "/history/%s/per_day_all_time_history.csv" % ccy)
        return dict([(h['DateTime'][:10], h['Average'])
                     for h in history])

class BitcoinVenezuela(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('api.bitcoinvenezuela.com', '/')
        rates = [(r, json['TWIST'][r]) for r in json['TWIST']
                 if json['TWIST'][r] is not None]  # Giving NULL sometimes
        return dict(rates)

    def protocol(self):
        return "http"

    def history_ccys(self):
        return ['ARS', 'EUR', 'USD', 'VEF']

    def historical_rates(self, ccy):
        json = self.get_json('api.bitcoinvenezuela.com',
                             '/historical/index.php?coin=TWIST')
        return json[ccy +'_TWIST']

class Bitfinex(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('api.bitfinex.com', '/v1/pubticker/TWISTusd')
        return {'USD': Decimal(json['last_price'])}

class BTCChina(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('data.btcchina.com', '/data/ticker?market=TWISTcny')
        return {'CNY': Decimal(json['ticker']['last'])}

class BTCe(ExchangeBase):
    def get_rates(self, ccy):
        ccys = ['EUR', 'RUR', 'USD']
        ccy_str = '-'.join(['TWIST_%s' % c.lower() for c in ccys])
        json = self.get_json('btc-e.com', '/api/3/ticker/%s' % ccy_str)
        result = dict.fromkeys(ccys)
        for ccy in ccys:
            result[ccy] = Decimal(json['TWIST_%s' % ccy.lower()]['last'])
        return result

class CaVirtEx(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.cavirtex.com', '/api2/ticker.json?currencypair=TWISTCAD')
        return {'CAD': Decimal(json['ticker']['TWISTCAD']['last'])}

class CoinSpot(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.coinspot.com.au', '/pubapi/latest')
        return {'AUD': Decimal(json['prices']['TWIST']['last'])}

class GoCoin(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('x.g0cn.com', '/prices')
        TWIST_prices = json['prices']['TWIST']
        return dict([(r, Decimal(TWIST_prices[r])) for r in TWIST_prices])

class HitBTC(ExchangeBase):
    def get_rates(self, ccy):
        ccys = ['EUR', 'USD']
        json = self.get_json('api.hitbtc.com', '/api/1/public/TWIST%s/ticker' % ccy)
        result = dict.fromkeys(ccys)
        if ccy in ccys:
            result[ccy] = Decimal(json['last'])
        return result

class Kraken(ExchangeBase):
    def get_rates(self, ccy):
        dicts = self.get_json('api.kraken.com', '/0/public/AssetPairs')
        pairs = [k for k in dicts['result'] if k.startswith('XTWISTZ')]
        json = self.get_json('api.kraken.com',
                             '/0/public/Ticker?pair=%s' % ','.join(pairs))
        ccys = [p[5:] for p in pairs]
        result = dict.fromkeys(ccys)
        result[ccy] = Decimal(json['result']['XTWISTZ'+ccy]['c'][0])
        return result

    def history_ccys(self):
        return ['EUR', 'USD']

    def historical_rates(self, ccy):
        query = '/0/public/OHLC?pair=TWIST%s&interval=1440' % ccy
        json = self.get_json('api.kraken.com', query)
        history = json['result']['XTWISTZ'+ccy]
        return dict([(time.strftime('%Y-%m-%d', time.localtime(t[0])), t[4])
                                    for t in history])

class OKCoin(ExchangeBase):
    def get_rates(self, ccy):
        json = self.get_json('www.okcoin.cn', '/api/ticker.do?symbol=TWIST_cny')
        return {'CNY': Decimal(json['ticker']['last'])}

class MercadoBitcoin(ExchangeBase):
    def get_rates(self,ccy):
        json = self.get_json('mercadobitcoin.net',
                                "/api/ticker/ticker_twist")
        return {'BRL': Decimal(json['ticker']['last'])}
    
    def history_ccys(self):
        return ['BRL']

class Bitcointoyou(ExchangeBase):
    def get_rates(self,ccy):
        json = self.get_json('bitcointoyou.com',
                                "/API/ticker_twist.aspx")
        return {'BRL': Decimal(json['ticker']['last'])}

    def history_ccys(self):
        return ['BRL']


def dictinvert(d):
    inv = {}
    for k, vlist in d.iteritems():
        for v in vlist:
            keys = inv.setdefault(v, [])
            keys.append(k)
    return inv

def get_exchanges():
    is_exchange = lambda obj: (inspect.isclass(obj)
                               and issubclass(obj, ExchangeBase)
                               and obj != ExchangeBase)
    return dict(inspect.getmembers(sys.modules[__name__], is_exchange))

def get_exchanges_by_ccy():
    "return only the exchanges that have history rates (which is hardcoded)"
    d = {}
    exchanges = get_exchanges()
    for name, klass in exchanges.items():
        exchange = klass(None, None)
        d[name] = exchange.history_ccys()
    return dictinvert(d)



class FxThread(ThreadJob):

    def __init__(self, config, network):
        self.config = config
        self.network = network
        self.ccy = self.get_currency()
        self.history_used_spot = False
        self.ccy_combo = None
        self.hist_checkbox = None
        self.exchanges = get_exchanges()
        self.exchanges_by_ccy = get_exchanges_by_ccy()
        self.set_exchange(self.config_exchange())

    def get_exchanges_by_ccy(self, ccy, h):
        return self.exchanges_by_ccy.get(ccy, [])

    def ccy_amount_str(self, amount, commas):
        prec = CCY_PRECISIONS.get(self.ccy, 2)
        fmt_str = "{:%s.%df}" % ("," if commas else "", max(0, prec))
        return fmt_str.format(round(amount, prec))

    def run(self):
        # This runs from the plugins thread which catches exceptions
        if self.is_enabled():
            if self.timeout ==0 and self.show_history():
                self.exchange.get_historical_rates(self.ccy)
            if self.timeout <= time.time():
                self.timeout = time.time() + 150
                self.exchange.update(self.ccy)

    def is_enabled(self):
        return bool(self.config.get('use_exchange_rate'))

    def set_enabled(self, b):
        return self.config.set_key('use_exchange_rate', bool(b))

    def get_history_config(self):
        return bool(self.config.get('history_rates'))

    def set_history_config(self, b):
        self.config.set_key('history_rates', bool(b))

    def get_currency(self):
        '''Use when dynamic fetching is needed'''
        return self.config.get("currency", "EUR")

    def config_exchange(self):
        return self.config.get('use_exchange', 'BTCe')

    def show_history(self):
        return self.is_enabled() and self.get_history_config() and self.ccy in self.exchange.history_ccys()

    def set_currency(self, ccy):
        self.ccy = ccy
        self.config.set_key('currency', ccy, True)
        self.timeout = 0 # Because self.ccy changes
        self.on_quotes()

    def set_exchange(self, name):
        class_ = self.exchanges.get(name) or self.exchanges.values()[0]
        name = class_.__name__
        self.print_error("using exchange", name)
        if self.config_exchange() != name:
            self.config.set_key('use_exchange', name, True)

        self.exchange = class_(self.on_quotes, self.on_history)
        # A new exchange means new fx quotes, initially empty.  Force
        # a quote refresh
        self.timeout = 0

    def on_quotes(self):
        self.network.trigger_callback('on_quotes')

    def on_history(self):
        self.network.trigger_callback('on_history')

    def exchange_rate(self):
        '''Returns None, or the exchange rate as a Decimal'''
        rate = self.exchange.quotes.get(self.ccy)
        if rate:
            return Decimal(rate)

    def format_amount_and_units(self, btc_balance):
        rate = self.exchange_rate()
        return '' if rate is None else "%s %s" % (self.value_str(btc_balance, rate), self.ccy)

    def get_fiat_status_text(self, btc_balance):
        rate = self.exchange_rate()
        return _("  (No FX rate available)") if rate is None else " 1 BTC~%s %s" % (self.value_str(COIN, rate), self.ccy)


    def value_str(self, satoshis, rate):
        if satoshis is None:  # Can happen with incomplete history
            return _("Unknown")
        if rate:
            value = Decimal(satoshis) / COIN * Decimal(rate)
            return "%s" % (self.ccy_amount_str(value, True))
        return _("No data")

    def history_rate(self, d_t):
        rate = self.exchange.historical_rate(self.ccy, d_t)
        # Frequently there is no rate for today, until tomorrow :)
        # Use spot quotes in that case
        if rate is None and (datetime.today().date() - d_t.date()).days <= 2:
            rate = self.exchange.quotes.get(self.ccy)
            self.history_used_spot = True
        return rate

    def historical_value_str(self, satoshis, d_t):
        rate = self.history_rate(d_t)
        return self.value_str(satoshis, rate)
