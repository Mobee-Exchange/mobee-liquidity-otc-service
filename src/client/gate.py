import time
import hmac
import hashlib
import requests


class GateioClients:
    def __init__(self, api_key: str, api_secret: str):
        self.host = "https://api.gateio.ws"
        self.prefix = "/api/v4"
        self.api_key = api_key
        self.api_secret = api_secret
        self.common_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def gen_sign(self, method: str, url: str, query_string: str = "", payload_string: str = "") -> dict:
        """Generate Gate.io HMAC SHA512 signature following official docs."""
        t = time.time()
        m = hashlib.sha512()
        m.update((payload_string or "").encode('utf-8'))
        hashed_payload = m.hexdigest()
        s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
        sign = hmac.new(self.api_secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
        return {'KEY': self.api_key, 'Timestamp': str(t), 'SIGN': sign}

    def get_dual_investment_orders(self, page: int = 1, from_ts: int = None) -> requests.Response:
        url = '/earn/dual/orders'
        params = {
            "from": from_ts or int(time.time()),
            "page": page,
            "limit": 100,
        }
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        sign_headers = self.gen_sign("GET", self.prefix + url, query_string=query_string)
        sign_headers.update(self.common_headers)

        try:
            response = requests.get(
                self.host + self.prefix + url + "?" + query_string,
                headers=sign_headers,
                timeout=10,
            )
            return response
        except requests.RequestException as e:
            raise Exception(f"Error fetching dual investment orders: {e}") from e