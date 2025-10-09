from .base import ProxyProvider, Proxy as ProxyBase
from utils.utils import generate_id
from omniprox.providers.cloudflare import CloudflareProvider as CloudflareProviderBase
from omniprox.providers.alibaba import AlibabaProvider as AlibabaProviderBase
from omniprox.providers.gcp import GCPProvider as GCPProviderBase
from omniprox.providers.azure import AzureProvider as AzureProviderBase
from omniprox.core.base import BaseOmniProx
import argparse
import logging
import json
import requests
import sys

def base_omni_prox_init(self, provider_name: str, args):
	self.provider = provider_name
	self.logger = logging.getLogger(f'omniprox.{provider_name}')
	self.args = args

	self.url = getattr(args, 'url', None)
	self.api_id = getattr(args, 'api_id', None)
	self.auto_create = False

# Overwrite original init class to prevent loading profile
BaseOmniProx.__init__ = base_omni_prox_init

class Args(object):
	pass

class CloudflareProvider(CloudflareProviderBase):
	""" Wrapper around CloudflareProvider from OmniProx to match interface """
	def __init__(self, config_dict, args):
		super().__init__(args)
		self.api_token = config_dict.get('api_token', '')
		self.account_id = config_dict.get('account_id', '')
		self.zone_id = config_dict.get('zone_id', '')
		self.proxies = []

	def _save_endpoint(self, endpoint):
		self.proxies.append(Proxy(
			proxy_url=endpoint['url'],
			api_key=endpoint['name'],
		))

class AlibabaProvider(AlibabaProviderBase):
	""" Wrapper around AlibabaProvider from OmniProx to match interface """
	def __init__(self, config_dict, args):
		super().__init__(args)
		self.access_key_id = config_dict.get('access_key_id')
		self.access_key_secret = config_dict.get('access_key_secret')
		self.region_id = config_dict.get('region_id', 'cn-hangzhou')

	@property
	def proxies(self):
		for api in self.apis:
			yield Proxy(
				proxy_url=api['proxy_url'],
				api_key=api['api_id'],
			)

class AzureProvider(AzureProviderBase):
	""" Wrapper around AzureProvider from OmniProx to match interface """
	def __init__(self, config_dict, args):
		super().__init__(args)
		self.subscription_id = config_dict.get('subscription_id')
		self.tenant_id = config_dict.get('tenant_id')
		self.client_id = config_dict.get('client_id')
		self.client_secret = config_dict.get('client_secret')
		self.location = config_dict.get('location', fallback='eastus')
		self.resource_group = config_dict.get('resource_group')
		self.use_cli = config_dict.get('use_cli', fallback='true').lower() == 'true'
		pool_json = config_dict.get('container_pool', fallback='[]')
		try:
			self.container_pool = json.loads(pool_json)
		except Exception:
			self.container_pool = []

	@property
	def proxies(self):
		for container in self.container_pool:
			yield Proxy(
				proxy_url=container['url'],
				api_key=container['name'],
			)


class GCPProvider(GCPProviderBase):
	""" Wrapper around GCPProvider from OmniProx to match interface """
	def __init__(self, config_dict, args):
		super().__init__(args)
		self.project_id = config_dict.get('project_id', '')
		self.credentials_path = config_dict.get('credentials_path', '')
		self.region = config_dict.get('region', 'us-central1')
		self.use_cli = config_dict.get('use_cli', '').lower() == 'true'

		# Set gcp-prefixed attributes for compatibility
		self.gcp_project_id = self.project_id
		self.gcp_credentials_path = self.credentials_path
		self.gcp_region = self.region
		self.proxies = []

	def _create_api_with_id(self, api_id):
		url = super()._create_api_with_id(api_id)
		self.proxies.append(Proxy(
			proxy_url=url,
			api_key=api_id,
		))
		return url

class Proxy(ProxyBase):
	def send_request(self, method, path="", session=None, **kwargs):
		url = f"{self.proxy_url}{path}"
		if not session:
			session = requests
		return session.request(method, url, **kwargs)

providers = {
	"cf": CloudflareProvider,
	"cloudflare": CloudflareProvider,
	"alibaba": AlibabaProvider,
	"azure": AzureProvider,
	"az": AzureProvider,
	"gcp": GCPProvider,
}

class OMNIProxyProvider(ProxyProvider):
	should_execute = True

	def parse_all_args(self, args, config_dict):

		parser = argparse.ArgumentParser(add_help=False)
		parser.add_argument('--provider', '-p',
		           choices=['gcp', 'azure', 'az', 'cloudflare', 'cf', 'alibaba'],
		           help='Cloud provider')

		args, extra_args = parser.parse_known_args(args)

		self.provider = args.provider or config_dict.get("provider")
		self.config_dict = config_dict

		return extra_args

	def create_apis(self, number, url):
		provider_class = providers[self.provider]
		args = Args()
		args.url = url
		args.number = number
		provider = provider_class(self.config_dict, args)
		provider.create()
		yield from provider.proxies

	def create_api(self, url):
		# Not necessary, because it is not called from create_apis
		pass

	def destroy_api(self, api):
		provider_class = providers[self.provider]
		args = Args()
		args.api_id = api.api_key
		provider = provider_class(self.config_dict, args)
		provider.delete()

	def do_input_error_handling(self):
		if not self.provider:
			self.logger.log_entry("Provider is required")
			sys.exit()
		

