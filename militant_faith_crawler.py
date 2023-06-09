
from datetime import datetime
import re
from time import time
from typing import List

from data import templar2num, num2templarmod, modtranslation2num, num2explicitmod, useful_seeds
from request_lib import RequestHandler, get_price_in_chaos, upload_data


r = RequestHandler()

class Jewel:
    seed: int
    templar: int
    price: int
    mod1: int
    mod2: int

    def __init__(self, trade_result):
        m = re.match(r'Carved to glorify (\d+) new faithful converted by High Templar (.*)\n', trade_result['item']['explicitMods'][0])
        seed, templar = m.group(1), m.group(2)
        self.seed = int(seed)
        self.templar = templar2num[templar]
        self.price = get_price_in_chaos(trade_result)
        self.mod1 = modtranslation2num[trade_result['item']['explicitMods'][1]]
        self.mod2 = modtranslation2num[trade_result['item']['explicitMods'][2]]
        

    def to_trade_filter_element(self):
        return {
            'id': num2templarmod[self.templar],
            'value': {
                'min': self.seed,
                'max': self.seed
            },
            'disabled': False
        }

def generate_trade_link(jewels: List[Jewel], mods):
    query_data = {
        'query':{
            'status':{
                'option':'online'
            },
            'stats':[
                {
                    'type':'and',
                    'filters':[
                    {
                        'id':  num2explicitmod[modtranslation2num[mod]]
                    } for mod in mods
                    ]
                },
                {
                    'filters':[
                        jewel.to_trade_filter_element() for jewel in [j for j in jewels if j.seed in useful_seeds][:35]
                    ],
                    'type':'count',
                    'value':{
                    'min':1
                    }
                }
            ]
        },
        'sort':{
            'price':'asc'
        }
    }
    url = f'https://www.pathofexile.com/api/trade/search/{r.current_league}'
    response = r.make_request(url, 'POST', query_data)
    return  f'https://www.pathofexile.com/trade/search/{r.current_league}/{response.json()["id"]}'


def crawl_trade(mods):
    jewels = []
    min_price = 0
    while len(jewels) < 35:
        post_response = make_post_request(min_price, mods)
        if post_response.json()["total"] <= 1:
            break
        for result in r.trade_fetch(post_response):
            jewel = Jewel(result)
            if jewel.price is not None:
                min_price = jewel.price + 1
                if jewel.seed in useful_seeds:
                    jewels.append(jewel)
                    if len(jewels) >= 35:
                        return generate_trade_link(sorted(jewels, key=lambda x: x.price), mods)
    return generate_trade_link(sorted(jewels, key=lambda x: x.price), mods)

def make_post_request(min_price, mods):
    query_data = {
        'query':{
            'status':{
                'option':'online'
            },
            'stats':[
                {
                    'type':'and',
                    'filters':[
                    {
                        'id':  num2explicitmod[modtranslation2num[mod]]
                    } for mod in mods
                    ]
                }
            ],      
            "filters": {
                "trade_filters": {
                    "filters": {
                        "price": {
                            "min": min_price
                        }
                    }
                }
            }
        },
        'sort':{
            'price':'asc'
        }
    }
    url = f'https://www.pathofexile.com/api/trade/search/{r.current_league}'
    return r.make_request(url, 'POST', query_data)


def grab_jewels():
    generic_link = crawl_trade(['1% increased effect of Non-Curse Auras per 10 Devotion'])
    mana_link = crawl_trade(['1% increased effect of Non-Curse Auras per 10 Devotion', '1% reduced Mana Cost of Skills per 10 Devotion'])
    return {'generic_link': generic_link, 'mana_link': mana_link, 'time_since_last_update': str(datetime.utcnow())}


def main():
    t = time()
    data = grab_jewels()
    r = upload_data("https://militant-faith-finder.fly.dev/upload", data)
    print(r.text)    
    print(time()-t)

if __name__ == '__main__':
    main()