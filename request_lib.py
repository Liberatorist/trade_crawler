from datetime import datetime, timedelta
from time import sleep
import time
from typing import Dict, List
import requests
import os
from ratelimiter import RateLimiter

headers = {
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0',
}

class Queue:
    queue = List[datetime.date]
    def __init__(self):
        self.queue = []

    def add(self):
        self.queue = [datetime.utcnow(), *self.queue]

    def get_sleep_time(self, time_interval: int, max_requests: int) -> timedelta:
        if len(self.queue) < max_requests + 1:
            return timedelta(seconds=0)        
        return max(timedelta(seconds=0), self.queue[max_requests] - datetime.utcnow() + timedelta(seconds=time_interval))

    def __str__(self):
        now = datetime.utcnow()
        return "\n".join(str(i) for i in self.queue)

class RequestHandler:

    def __init__(self):
        self.headers = {
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0',
        }
        self.cookies = {}
        self.get_is_initialized = False
        self.make_limited_get_request = None
        self.post_is_initialized = False
        self.make_limited_post_request = None
        self.queue: Dict(str, Queue) = {"GET": Queue(), "POST": Queue()}
        self.current_league = self.set_league()

    def set_league(self):
        response = requests.get('https://api.pathofexile.com/leagues', headers=self.headers, cookies=self.cookies)
        for league in response.json():
            if league['rules'] == [] and 'This is the default Path of Exile league' in league['description']:
                return league['id']
        return "Crucible"  # if league cant be found

    def trade_fetch(self, post_response):
        url_hash = post_response.json()['id']
        results = post_response.json()['result']
        for items in [','.join(results[n: n + 10]) for n in range(0, len(results), 10)]:
            url = f'https://www.pathofexile.com/api/trade/fetch/{items}?query={url_hash}'
            response = self.make_request(url, 'GET')
            for result in response.json()['result']:
                yield result
    
    
    def make_request(self, url, method, data=None):
        if method == 'GET':
            response = self.make_get_request(url, self.headers, self.cookies)
        elif method == 'POST':
            response = self.make_post_request(url, self.headers, self.cookies, data)
        else:
            return None
        if response.status_code > 399:
            print(response.headers['X-Rate-Limit-Ip'], response.headers['X-Rate-Limit-Ip-State'])
            raise ConnectionError(response.text)
        return response        


    def initialize_limited_request(self, response_headers, method):
        policies, current_states = response_headers['X-Rate-Limit-Ip'], response_headers['X-Rate-Limit-Ip-State']
        limiters = [RateLimiter(period=1, max_calls=10000) for _ in range(3)]
        for idx, policy, state in zip(range(3), policies.split(','), current_states.split(',')):
            request_limit, period, _ = policy.split(':')
            current_state, _, _ = state.split(':')
            limiter = RateLimiter(period=int(int(period) * 1.1), max_calls=int(request_limit))
            limiter.calls.extend(time.time() for _ in range(int(current_state))) # add previous requests to queue
            limiters[idx] = limiter


        @limiters[0]
        @limiters[1]
        @limiters[2]
        def limit_request_function(url, headers, cookies, data=None):
            if data:
                return getattr(requests, method)(url, headers=headers, cookies=cookies, json=data)
            return getattr(requests, method)(url, headers=headers, cookies=cookies)
        return limit_request_function    

    def make_get_request(self, url, headers, cookies):
        if self.get_is_initialized:
            return self.make_limited_get_request(url, headers, cookies)
        else:
            response = requests.get(url, headers=headers, cookies=cookies)
            self.make_limited_get_request = self.initialize_limited_request(response.headers, "get")
            self.get_is_initialized = True
            return response
        
    def make_post_request(self, url, headers, cookies, data):
        if self.post_is_initialized:
            return self.make_limited_post_request(url, headers, cookies, data)
        else:
            response = requests.post(url, headers=headers, cookies=cookies, json=data)
            self.make_limited_post_request = self.initialize_limited_request(response.headers, "post")
            self.post_is_initialized = True
            return response
        
    
def get_price_in_chaos(result):
    price_data = result['listing']['price']
    div_price = 220
    if price_data['currency'] == 'chaos':
        return round(price_data['amount'])
    elif price_data['currency'] == 'divine':
        return round(price_data['amount'] * div_price)
    return None


def get_price_in_div(result):
    price_data = result['listing']['price']
    div_price = 220
    if price_data['currency'] == 'chaos':
        return round(price_data['amount'] / div_price, 2)
    elif price_data['currency'] == 'divine':
        return price_data['amount']
    return None


def upload_data(upload_url: str, data):
    data["pw"] = os.environ.get("UPLOAD_KEY", "")
    return requests.post(upload_url, json=data, headers=headers)
