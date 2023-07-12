import datetime as dt
import time
import requests
import pandas as pd
import traceback
import scams as scam_filter
import warnings

# pandas settings
########################################################################################################################
pd.options.mode.chained_assignment = None  # default='warn'
pd.set_option('display.max_columns', 200)
pd.set_option("display.max_rows", 800)
desired_width = 500
pd.set_option('display.width', desired_width)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning) # ignores pandas performance warnings
warnings.simplefilter(action='ignore', category=FutureWarning) # ignores pandas future warnings
########################################################################################################################

def fetch_wallet_balance(address, chain):

    api_key = ""
    api_url = 'https://api.covalenthq.com'
    endpoint = f'/v1/{chain}/address/{address}/balances_v2/'
    print(endpoint)
    url = api_url + endpoint
    r = requests.get(url, auth=(api_key,''))
    if r.status_code != 200:
        print(r, address, chain)
    return r


def get_balances(addresses):

    chain_ids = {"ethereum": 1, "polygon": 137, "avax c-chain": 43114, "bsc": 56, "arbitrum": 42161, "fantom": 250, "arbitrum-nova": 42170, "canto": 7700, "evmos": 9001, "metis": 1088}

    coin_positions = []
    farm_positions = []
    token_data = {}
    print(f"chain_ids: {chain_ids}")

    for address in addresses:
        for chain, id_ in chain_ids.items():
            try:
                chain_balance = fetch_wallet_balance(address, id_)
                if chain_balance.status_code == 200:
                    chain_balance = chain_balance.json()

                    if chain_balance["data"]:   # if there is actual data returned from api call
                        for token in chain_balance["data"]["items"]:

                            if token["contract_ticker_symbol"] is not None:
                                ticker = token["contract_ticker_symbol"].lower()
                            else:
                                ticker = "NONE"

                            if token["contract_name"] is not None:
                                contract_name = token["contract_name"].lower()
                            else:
                                contract_name = "NONE"

                            contract_address = token["contract_address"]
                            decimals = token["contract_decimals"]

                            balance =token["balance"]
                            balance = round(float(f"{balance[:-decimals]}.{balance[-decimals:]}"),1)

                            price = token["quote_rate"]
                            if price is None:
                                price = 0

                            usd_val = round((balance * price) / 10 ** 6, 5)  # milions

                            # FILTERING OUT SCAMS ------------------------------------------------------------------------
                            # if price is lower than 3 decimals consider it a scam
                            scam_price = True
                            include_tokens = ["shib"]   # hack to include coin if it's legit and not in scam price range
                            if float(price) > 0.0009999 and float(price) < 150000:  # my way to eliminate cca 90% of scam coins
                                scam_price = False
                            else:
                                if ticker in include_tokens:
                                    scam_price = False

                            scams = scam_filter.scams
                            scam_contracts = scam_filter.scam_contracts

                            scam_filters = [".io", ".net", ".com", ".org", ".app"]  # filter for generic scam token names
                            for filter_ in scam_filters:
                                if filter_ in ticker:
                                    scams.append(ticker)
                            # ------------------------------------------------------------------------
                            good_contracts = ["0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"]
                            if ticker not in scams and contract_address not in scam_contracts and not scam_price:
                                if price == 0:
                                    if balance > 0:
                                        farm_positions.append([ticker, balance])
                                else:
                                    if usd_val > 0.001 and (usd_val < 3000 or contract_address in good_contracts):   # spot coin positions above 1k and below 3bil(also way to filter out spam) ofc could delete the line and would work fine
                                        coin_positions.append([ticker,balance, usd_val])
                                        # print(f"adding {ticker} || prc: {price} || val. [mil]: {usd_val}")

                                        if ticker not in token_data.keys():
                                            token_data[ticker] = [contract_address, price]

                        time.sleep(0.5)     # just so I don't exceed api request limits
            except:
                print(f"failed getting data for: {address}|| chain: {id_}")
                traceback.print_exc()

    if coin_positions:
        coin_positions = pd.DataFrame(coin_positions, columns=["token","coins", "usd value[mil]"])
        coin_positions = coin_positions.groupby(['token']).sum()
        coin_positions.sort_values(by=["usd value[mil]"], ascending=False, inplace=True)
        coin_positions["coins"] = round(coin_positions["coins"],1)
        coin_positions["coins"] = coin_positions["coins"].astype(str)
        total_value = coin_positions["usd value[mil]"].sum()
        coin_positions["holding %"] = round(coin_positions["usd value[mil]"]/total_value*100,2)

        coin_positions["contract_address"] = None
        coin_positions["price"] = None

        for token in token_data.keys():
            coin_positions.at[token, "contract_address"] = token_data[token][0]
            coin_positions.at[token, "price"] = token_data[token][1]


        return coin_positions
    else:
        coin_positions = []
        return coin_positions




wallets = ["0x3DdfA8eC3052539b6C9549F12cEA2C295cfF5296", "0x176F3DAb24a159341c0509bB36B833E7fdd0a132"]


balances = get_balances(wallets)

print(balances)