import time
import hmac
import hashlib
import requests


class BinanceClients:
    def __init__(self, api_key: str, api_secret: str):
        self.base_url = "https://api.binance.com"
        self.api_key = api_key
        self.api_secret = api_secret

    def generate_signature(self, params: dict, secret: str):
        """Generate HMAC SHA256 signature."""
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        signature = hmac.new(
            secret.encode(), query_string.encode(), hashlib.sha256
        ).hexdigest()
        return signature

    def get_dual_investment_positions(
        self, status: str, pageIndex: int = None
    ) -> requests.Response:
        endpoint = "/sapi/v1/dci/product/positions"
        url = self.base_url + endpoint

        # Define parameters with timestamp
        if pageIndex is None:
            pageIndex = 1

        params = {
            "status": status,
            "timestamp": int(time.time() * 1000),
            "pageSize": 100,
            "pageIndex": pageIndex,
        }

        headers = {"X-MBX-APIKEY": self.api_key}
        params["signature"] = self.generate_signature(params, self.api_secret)
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            return response
        except requests.RequestException as e:
            raise Exception(f"Error fetching dual investment positions: {e}") from e
