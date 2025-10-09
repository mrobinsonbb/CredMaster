from dataclasses import dataclass
from abc import ABC, abstractmethod

class ProxyProvider(ABC):
	def __init__(self, logger):
		self.logger = logger

	@abstractmethod
	def parse_all_args(self, args, config_dict):
		pass

	def do_input_error_handling(self):
		pass

	def create_apis(self, number, url):
		for _ in range(number):
			yield self.create_api(url)

	@abstractmethod
	def create_api(self, url):
		pass

	@abstractmethod
	def destroy_api(self, api):
		pass

@dataclass
class Proxy:
	proxy_url: str
	api_key: str

	@abstractmethod
	def send_request(self, method, path="", headers=None, data=None, session=None, **kwargs):
		pass

	def post(self, *args, **kwargs):
		return self.send_request("POST", *args, **kwargs)
	
	def get(self, *args, **kwargs):
		return self.send_request("GET", *args, **kwargs)
