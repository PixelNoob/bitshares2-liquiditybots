from .basestrategy import BaseStrategy, MissingSettingsException
import math
from numpy import linspace


class MakerSellBuyWalls(BaseStrategy):
    """ Play Buy/Sell Walls into a market

        **Settings**:

        * **target_price**: target_price to place Ramps around (floating number or "feed")
        * **target_price_offset_percentage**: +-percentage offset from target_price
        * **spread_percentage**: Another "offset". Allows a spread. The lowest orders will be placed here
        * **volume_percentage**: The amount of funds (%) you want to use
        * **symmetric_sides**: (boolean) Place symmetric walls on both sides?
        * **only_buy**: Serve only on of both sides 
        * **only_sell**: Serve only on of both sides 

        .. code-block:: python

            bots["MakerWall"] = {"bot" : MakerSellBuyWalls,
                                 "markets" : ["USD : BTS"],
                                 "target_price" : "feed",
                                 "target_price_offset_percentage" : 5,
                                 "spread_percentage" : 5,
                                 "volume_percentage" : 10,
                                 "symmetric_sides" : True,
                                 "only_buy" : False,
                                 "only_sell" : False,
                                 }

        .. note:: This module does not watch your orders, all it does is
                  place new orders!
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self):
        """ set default settings
        """
        if "target_price_offset_percentage" not in self.settings:
            self.settings["target_price_offset_percentage"] = 0.0

        if "target_price" not in self.settings:
            raise MissingSettingsException("target_price")

        if "spread_percentage" not in self.settings:
            raise MissingSettingsException("spread_percentage")

        if "volume_percentage" not in self.settings:
            raise MissingSettingsException("volume_percentage")

        if "symmetric_sides" not in self.settings:
            self.settings["symmetric_sides"] = True

        # Place orders
        # self.place()

    def orderFilled(self, oid):
        """ Do nothing, when an order is Filled
        """
        pass

    def place(self) :
        """ Place all orders according to the settings.
        """
        print("Placing Orders:")
        target_price = self.settings["target_price"]
        only_sell = True if "only_sell" in self.settings and self.settings["only_sell"] else False
        only_buy = True if "only_buy" in self.settings and self.settings["only_buy"] else False

        #: Amount of Funds available for trading (per asset)
        balances = self.dex.returnBalances()
        asset_ids = []
        amounts = {}
        for market in self.settings["markets"] :
            quote, base = market.split(self.config.market_separator)
            asset_ids.append(base)
            asset_ids.append(quote)
        assets_unique = list(set(asset_ids))
        for a in assets_unique:
            if a in balances :
                amounts[a] = balances[a] * self.settings["volume_percentage"] / 100 / asset_ids.count(a)

        ticker = self.dex.returnTicker()
        for m in self.settings["markets"]:

            if isinstance(target_price, float) or isinstance(target_price, int):
                base_price = float(target_price) * (1 + self.settings["target_price_offset_percentage"] / 100)
            elif (isinstance(target_price, str) and
                  target_price is "settlement_price" or
                  target_price is "feed" or
                  target_price is "price_feed"):
                if "settlement_price" in ticker[m] :
                    base_price = ticker[m]["settlement_price"] * (1 + self.settings["target_price_offset_percentage"] / 100)
                else :
                    raise Exception("Pair %s does not have a settlement price!" % m)

            buy_price  = base_price * (1.0 - self.settings["spread_percentage"] / 200)
            sell_price = base_price * (1.0 + self.settings["spread_percentage"] / 200)

            quote, base = m.split(self.config.market_separator)
            if quote in amounts and not only_buy:
                if "symmetric_sides" in self.settings and self.settings["symmetric_sides"] and not only_sell:
                    thisAmount = min([amounts[quote], amounts[base] / buy_price]) if base in amounts else amounts[quote]
                    self.sell(m, sell_price, thisAmount)
                else :
                    self.sell(m, sell_price, amounts[quote])
            if base in amounts and not only_sell:
                if "symmetric_sides" in self.settings and self.settings["symmetric_sides"] and not only_buy:
                    thisAmount = min([amounts[quote], amounts[base] / buy_price]) if quote in amounts else amounts[base] / buy_price
                    self.buy(m, buy_price, thisAmount)
                else :
                    self.buy(m, buy_price, amounts[base] / buy_price)


class MakerRamp(BaseStrategy):

    """ Play Buy/Sell Walls into a market

        **Settings**:

        * **target_price**: target_price to place Ramps around (floating number or "feed")
        * **target_price_offset_percentage**: +-percentage offset from target_price
        * **spread_percentage**: Another "offset". Allows a spread. The lowest orders will be placed here
        * **volume_percentage**: The amount of funds (%) you want to use
        * **only_buy**: Serve only on of both sides 
        * **only_sell**: Serve only on of both sides 
        * **ramp_mode**: "linear" ramp (equal amounts) or "exponential" (linearily increasing amounts)
        * **ramp_price_percentage**: Ramp goes up with volume up to a price increase of x%
        * **ramp_step_percentage**: from spread/2 to ramp_price, place an order every x%
        * **expiration**: expiration time of buy/sell orders.
        
        .. code-block:: python

            bots["MakerRexp"] = {"bot" : MakerRamp,
                                 "markets" : ["USD : BTS"],
                                 "target_price" : "feed",
                                 "target_price_offset_percentage" : 5,
                                 "spread_percentage" : 0.2,
                                 "volume_percentage" : 30,
                                 "ramp_price_percentage" : 2,
                                 "ramp_step_percentage" : 0.3,
                                 "ramp_mode" : "linear",
                                 "only_buy" : False,
                                 "only_sell" : False,
                                 "expiration": 60*60*24*7
                                 }

        .. note:: This module does not watch your orders, all it does is
                  place new orders!

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self) :
        """ set default settings
        """
        if "target_price_offset_percentage" not in self.settings:
            self.settings["target_price_offset_percentage"] = 0.0

        if "target_price" not in self.settings:
            raise MissingSettingsException("target_price")

        if "spread_percentage" not in self.settings:
            raise MissingSettingsException("spread_percentage")

        if "volume_percentage" not in self.settings:
            raise MissingSettingsException("volume_percentage")

        if "ramp_price_percentage" not in self.settings:
            raise MissingSettingsException("ramp_price_percentage")

        if "ramp_step_percentage" not in self.settings:
            raise MissingSettingsException("ramp_step_percentage")

        if "ramp_mode" not in self.settings:
            self.settings["ramp_mode"] = "linear"

        # Place orders
        #self.place()

    def orderFilled(self, oid):
        #print("Order filled: %s" % oid)
        # Might be buggy
        pass
        
    def orderPlaced(self, oid):
        #print("Order succesfully placed: %s" % oid)
        pass

    def place(self) :
            """ Place all orders according to the settings.
            """
            print("Placing Orders:")
            #: Amount of Funds available for trading (per asset)
            if "ramp_mode" not in self.settings:
                mode = "linear"
            else :
                mode = self.settings["ramp_mode"]
            target_price = self.settings["target_price"]
            only_sell = True if "only_sell" in self.settings and self.settings["only_sell"] else False
            only_buy = True if "only_buy" in self.settings and self.settings["only_buy"] else False

            balances = self.dex.returnBalances()
            asset_ids = []
            amounts = {}
            for market in self.settings["markets"]:
                quote, base = market.split(self.config.market_separator)
                asset_ids.append(base)
                asset_ids.append(quote)
            assets_unique = list(set(asset_ids))
            for a in assets_unique:
                if a in balances :
                    amounts[a] = balances[a] * self.settings["volume_percentage"] / 100 / asset_ids.count(a)

            ticker = self.dex.returnTicker()
            for m in self.settings["markets"]:

                quote, base = m.split(self.config.market_separator)
                if isinstance(target_price, float) or isinstance(target_price, int):
                    base_price = float(target_price)
                elif (isinstance(target_price, str) and
                      target_price is "settlement_price" or
                      target_price is "feed" or
                      target_price is "price_feed"):
                    if "settlement_price" in ticker[m] :
                        base_price = ticker[m]["settlement_price"]
                    else :
                        raise Exception("Pair %s does not have a settlement price!" % m)

                    base_price = base_price * (1 + self.settings["target_price_offset_percentage"] / 100)

                if quote in amounts and not only_buy:
                    price_start  = base_price * (1 + self.settings["spread_percentage"] / 200.0)
                    price_end    = base_price * (1 + self.settings["ramp_price_percentage"] / 100.0)
                    if not only_sell :
                        amount       = min([amounts[quote], amounts[base] / (price_start)]) if base in amounts else amounts[quote]
                    else:
                        amount = amounts[quote]
                    number_orders = math.floor((self.settings["ramp_price_percentage"] / 100.0 - self.settings["spread_percentage"] / 200.0) / (self.settings["ramp_step_percentage"] / 100.0))
                    if mode == "linear" :
                        for price in linspace(price_start, price_end, number_orders) :
                            self.sell(m, price, amount / number_orders)
                    elif mode == "exponential" :
                        k = linspace(1 / number_orders, 1, number_orders)
                        k = [v / sum(k) for v in k]
                        order_amounts = [v * amount for v in k]
                        for i, price in enumerate(linspace(price_start, price_end, number_orders)):
                            self.sell(m, price, order_amounts[i])
                    else :
                        raise Exception("ramp_mode '%s' not known" % mode)

                if base in amounts and not only_sell:
                    price_start  = base_price * (1 - self.settings["spread_percentage"] / 200.0)
                    price_end    = base_price * (1 - self.settings["ramp_price_percentage"] / 100.0)
                    if not only_buy:
                        amount       = min([amounts[quote], amounts[base] / (price_start)]) if quote in amounts else amounts[base] / (price_start)
                    else:
                        amount = amounts[base] / price_start
                    number_orders = math.floor((self.settings["ramp_price_percentage"] / 100.0 - self.settings["spread_percentage"] / 200.0) / (self.settings["ramp_step_percentage"] / 100.0))
                    if mode == "linear" :
                        for price in linspace(price_start, price_end, number_orders) :
                            self.buy(m, price, amount / number_orders)
                    elif mode == "exponential" :
                        k = linspace(1 / number_orders, 1, number_orders)
                        k = [v / sum(k) for v in k]
                        order_amounts = [v * amount for v in k]
                        for i, price in enumerate(linspace(price_start, price_end, number_orders)):
                            self.buy(m, price, order_amounts[i])
                    else :
                        raise Exception("ramp_mode '%s' not known" % mode)

    def sell(self, market, price, amount):
        """ Places a sell order in a given market (sell ``quote``, buy
            ``base`` in market ``quote_base``). Required POST parameters
            are "currencyPair", "rate", and "amount". If successful, the
            method will return the order creating (signed) transaction.

            :param str currencyPair: Return results for a particular market only (default: "all")
            :param float price: price denoted in ``base``/``quote``
            :param number amount: Amount of ``quote`` to sell

            Prices/Rates are denoted in 'base', i.e. the USD_BTS market
            is priced in BTS per USD.

            **Example:** in the USD_BTS market, a price of 300 means
            a USD is worth 300 BTS

            .. note::

                All prices returned are in the **reversed** orientation as the
                market. I.e. in the BTC/BTS market, prices are BTS per BTS.
                That way you can multiply prices with `1.05` to get a +5%.
        """
        quote, base = market.split(self.config.market_separator)
        print(" - Selling %f %s for %s @%f %s/%s" % (amount, quote, base, price, base, quote))
        self.dex.sell(market, price, amount, expiration=self.settings["expiration"])

    def buy(self, market, price, amount):
        """ Places a buy order in a given market (buy ``quote``, sell
            ``base`` in market ``quote_base``). Required POST parameters
            are "currencyPair", "rate", and "amount". If successful, the
            method will return the order creating (signed) transaction.

            :param str currencyPair: Return results for a particular market only (default: "all")
            :param float price: price denoted in ``base``/``quote``
            :param number amount: Amount of ``quote`` to buy

            Prices/Rates are denoted in 'base', i.e. the USD_BTS market
            is priced in BTS per USD.

            **Example:** in the USD_BTS market, a price of 300 means
            a USD is worth 300 BTS

            .. note::

                All prices returned are in the **reveresed** orientation as the
                market. I.e. in the BTC/BTS market, prices are BTS per BTS.
                That way you can multiply prices with `1.05` to get a +5%.
        """
        quote, base = market.split(self.config.market_separator)
        print(" - Buying %f %s with %s @%f %s/%s" % (amount, quote, base, price, base, quote))
        self.dex.buy(market, price, amount, expiration=self.settings["expiration"])
