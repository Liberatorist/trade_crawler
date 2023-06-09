from datetime import datetime
import json
import re
import sqlite3 as sl
from typing import List
from request_lib import RequestHandler, get_price_in_div, upload_data

num2type = ["Brutal Restraint","Glorious Vanity","Elegant Hubris"]
type2num = {k:v for v, k in enumerate(num2type)}


def connect_to_db():
    return sl.connect('trade.db')


def get_jewels():
    con = connect_to_db()
    with con:
        response = con.execute("SELECT * FROM JEWELS ORDER BY price")
    for r in response:
        yield Jewel(*r)


def get_impossible_escapes():
    con = connect_to_db()
    with con:
        response = con.execute("SELECT * FROM IMPOSSIBLE_ESCAPES ORDER BY price")
    for r in response:
        yield ImpossibleEscape(*r)


r = RequestHandler()


class Jewel:
    def __init__(self, seed, type, last_seen, price):
        self.seed = seed
        self.type = num2type[type]
        self.last_seen = datetime.strptime(last_seen, '%Y-%m-%d %H:%M') if last_seen else None
        self.price = float(price) if (price is not None and price != "None") else None

class ImpossibleEscape:
    def __init__(self, keystone, name, last_seen, price):
        self.keystone = keystone
        self.name = name
        self.last_seen = datetime.strptime(last_seen, '%Y-%m-%d %H:%M') if last_seen else None
        self.price = float(price) if (price is not None and price != "None") else None


versions = {
    "Glorious Vanity": ["xibaqua", "doryani", "ahuana"],
    "Brutal Restraint": ["asenath", "balbala", "nasima"],
    "Elegant Hubris": ["cadiro", "caspiro", "victario"]
}


def trade_for_impossible_escapes(impossible_escapes: List[ImpossibleEscape]):
    url = f"https://www.pathofexile.com/api/trade/search/{r.current_league}"
    query_data = {
        "query":{
            "status":{
                "option":"onlineleague"
            },
            "stats":[
                {
                    "type":"count",
                    "filters":[
                    {
                        "id":"explicit.stat_2422708892",
                        "value":{
                            "option":ie.keystone
                        },
                        "disabled":False
                    } for ie in impossible_escapes
                    ],
                    "value":{
                    "min":1
                    }
                }
            ]
        },
        "sort":{
            "price":"asc"
        }
    }
    return r.make_request(url, "POST", query_data)


def trade_for_jewels(jewels: List[Jewel]):
    url = f"https://www.pathofexile.com/api/trade/search/{r.current_league}"
    query_data = {
        "query": {
            "status": {
                "option": "onlineleague"
            },
            "stats": [
                {
                    "type": "count",
                    "filters": [
                        {
                            "id": f"explicit.pseudo_timeless_jewel_{version}",
                            "value": {
                                "min": jewel.seed,
                                "max": jewel.seed
                            },
                            "disabled": False
                        }
                        for jewel in jewels
                        for version in versions[jewel.type]
                    ],
                    "value": {
                        "min": 1
                    }
                }
            ]
        },
        "sort": {
            "price": "asc"
        }
    }
    return r.make_request(url, "POST", query_data)


def update_all_jewels():
    prices = []
    start_time = datetime.utcnow()
    print(f"Starting jewel update at {start_time}")
    jewels = list(get_jewels())
    k = 12
    for jewels_subset in [jewels[n: n + k] for n in range(0, len(jewels), k)]:
        seen_already = set()
        post_response = trade_for_jewels(jewels_subset)#
        for result in r.trade_fetch(post_response):
            seed = re.findall('\d+', result["item"]["explicitMods"][0])[0]
            jewel_type = type2num[result["item"]["name"]]

            if (seed, jewel_type) in seen_already:
                continue
            else:
                price = get_price_in_div    (result)
                if price is None:
                    continue
                prices.append([price, seed, jewel_type])
                seen_already.add((seed, jewel_type))       
            if len(seen_already) == len(jewels_subset):
                break

    print(f"Finished jewel updates at {datetime.utcnow()} after {(datetime.utcnow() - start_time).seconds}s")
    return prices


def update_all_impossible_escapes():
    start_time = datetime.utcnow()
    print(f"Starting IE update at {start_time}")
    prices = []
    impossible_escapes = list(get_impossible_escapes())
    k = 4
    for impossible_escapes_subset in [impossible_escapes[n: n + k] for n in range(0, len(impossible_escapes), k)]:
        post_response = trade_for_impossible_escapes(impossible_escapes_subset)
        seen_already = set()
        for result in r.trade_fetch(post_response):
            keystone = re.findall('Passives in Radius of (.*) can be Allocated', result["item"]["explicitMods"][0])[0]
            if keystone in seen_already:
                continue
            else:
                price = get_price_in_div(result)
                if price is None:
                    continue
                prices.append((price, keystone))
                seen_already.add(keystone)
            if len(seen_already) == len(impossible_escapes_subset):
                break
    print(f"Finished IE updates at {datetime.utcnow()} after {(datetime.utcnow() - start_time).seconds}s")
    return prices

def update_all():
    prices = dict()
    prices["jewels"] = update_all_jewels()
    prices["ie"] = update_all_impossible_escapes()
    r = upload_data("https://timeless-jewel-register.fly.dev/upload", prices)
    print(r.text)


if __name__ == '__main__':
    update_all()
