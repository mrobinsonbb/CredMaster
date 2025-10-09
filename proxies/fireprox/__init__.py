from ..base import ProxyProvider, Proxy
import requests
import utils.utils as utils
import sys
import argparse
from .fire import FireProx
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class AWS_API(Proxy):
	api_gateway_id: str

	def __init__(self, *args, api_gateway_id, **kwargs):
		super().__init__(*args, **kwargs)
		self.api_gateway_id = api_gateway_id

	def send_request(self, method, path="", headers=None, data=None, session=None, **kwargs):
		spoofed_ip = utils.generate_ip()
		amazon_id = utils.generate_id()
		trace_id = utils.generate_trace_id()

		headers["X-My-X-Forwarded-For"]= spoofed_ip
		headers["x-amzn-apigateway-api-id"]= amazon_id
		headers["X-My-X-Amzn-Trace-Id"]= trace_id

		url = f"{self.proxy_url}{path}"

		if not session:
			session = requests
		return session.request(method, url, headers=headers, data=data, **kwargs)

class FireproxProvider(ProxyProvider):
	should_execute = False
	regions = [
		"us-east-2", "us-east-1","us-west-1","us-west-2","eu-west-3",
		"ap-northeast-1","ap-northeast-2","ap-south-1",
		"ap-southeast-1","ap-southeast-2","ca-central-1",
		"eu-central-1","eu-west-1","eu-west-2","sa-east-1",
	]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.logger.log_entry(f"Total Regions Available: {len(self.regions)}")

	def parse_all_args(self, args, config_dict):

		parser = argparse.ArgumentParser(add_help=False)
		parser.add_argument('--region', default=None, required=False, help='Specify AWS Region to create API Gateways in')

		fp_args = parser.add_argument_group(title='Fireprox Connection Inputs')
		fp_args.add_argument('--profile_name', '--profile', type=str, default=None, help='AWS Profile Name to store/retrieve credentials')
		fp_args.add_argument('--access_key', type=str, default=None, help='AWS Access Key')
		fp_args.add_argument('--secret_access_key', type=str, default=None, help='AWS Secret Access Key')
		fp_args.add_argument('--session_token', type=str, default=None, help='AWS Session Token')

		fpu_args = parser.add_argument_group(title='Fireprox Utility Options')
		fpu_args.add_argument('--clean', default=False, action="store_true", help='Clean up all fireprox AWS APIs from every region, warning irreversible')
		fpu_args.add_argument('--api_destroy', type=str, default=None, help='Destroy single API instance, by API ID')
		fpu_args.add_argument('--api_list', default=False, action="store_true", help='List all fireprox APIs')

		args, extra_args = parser.parse_known_args(args)

		self.region = args.region or config_dict.get("region")
		self.access_key = args.access_key or config_dict.get("access_key")
		self.secret_access_key = args.secret_access_key or config_dict.get("secret_access_key")
		self.session_token = args.session_token or config_dict.get("session_token")
		self.profile_name = args.profile_name or config_dict.get("profile_name")

		if args.clean:
			self.proxy.clear_all_apis()
		elif args.api_destroy != None:
			self.destroy_single_api(args.api_destroy)
		elif args.api_list:
			self.list_apis()
		else:
			self.should_execute = True

		return extra_args

	def do_input_error_handling(self):
		# AWS Key Handling
		if self.session_token is not None and (self.secret_access_key is None or self.access_key is None):
			self.logger.log_entry("Session token requires access_key and secret_access_key")
			sys.exit()
		if self.profile_name is not None and (self.access_key is not None or self.secret_access_key is not None):
			self.logger.log_entry("Cannot use a passed profile and keys")
			sys.exit()
		if self.access_key is not None and self.secret_access_key is None:
			self.logger.log_entry("access_key requires secret_access_key")
			sys.exit()
		if self.access_key is None and self.secret_access_key is not None:
			self.logger.log_entry("secret_access_key requires access_key")
			sys.exit()
		if self.access_key is None and self.secret_access_key is None and self.session_token is None and self.profile_name is None:
			self.logger.log_entry("No FireProx access arguments settings configured, add access keys/session token or fill out config file")
			sys.exit()

		# Region handling
		if self.region is not None and self.region not in self.regions:
			self.logger.log_entry(f"Input region {self.region} not a supported AWS region, {self.regions}")
			sys.exit()

	def list_apis(self):

		for region in self.regions:

			args, help_str = self.get_fireprox_args("list", region)
			fp = FireProx(args, help_str)
			active_apis = fp.list_api()
			self.logger.log_entry(f"Region: {region} - total APIs: {len(active_apis)}")

			if len(active_apis) != 0:
				for api in active_apis:
					self.logger.log_entry(f"API Info --	 ID: {api['id']}, Name: {api['name']}, Created Date: {api['createdDate']}")

	def destroy_single_api(self, api):

		self.logger.log_entry("Destroying single API, locating region...")
		for region in self.regions:

			args, help_str = self.get_fireprox_args("list", region)
			fp = FireProx(args, help_str)
			active_apis = fp.list_api()

			for api1 in active_apis:
				if api1["id"] == api:
					self.logger.log_entry(f"API found in region {region}, destroying...")
					fp.delete_api(api)
					sys.exit()

			self.logger.log_entry("API not found")


	def destroy_api(self, api):
		args, help_str = self.get_fireprox_args("delete", api.api_key, api_id = api.api_gateway_id)
		fp = FireProx(args, help_str)
		self.logger.log_entry(f"Destroying API ({args['api_id']}) in region {api.api_key}")
		fp.delete_api(args["api_id"])

	def clear_all_apis(self):

		self.logger.log_entry("Clearing APIs for all regions")
		clear_count = 0

		for region in self.regions:

			args, help_str = self.get_fireprox_args("list", region)
			fp = FireProx(args, help_str)
			active_apis = fp.list_api()
			count = len(active_apis)
			err = "skipping"
			if count != 0:
				err = "removing"
			self.logger.log_entry(f"Region: {region}, found {count} APIs configured, {err}")

			for api in active_apis:
				if "fireprox" in api["name"]:
					fp.delete_api(api["id"])
					clear_count += 1

		self.logger.log_entry(f"APIs removed: {clear_count}")

	def create_apis(self, number, url):
		if number > len(self.regions):
			raise Exception("Thread count over maximum, reduce it to 15")

		# slow but multithreading this causes errors in boto3 for some reason :(
		for x in range(number):
			reg = self.regions[x]
			if self.region is not None:
				reg = self.region
			api = self.create_api(reg, url)
			self.logger.log_entry(f"Created API - Region: {reg} ID: ({api.api_gateway_id}) - {api.proxy_url} => {url}")
			yield api

	def create_api(self, region, url):
		print(region)
		args, help_str = self.get_fireprox_args("create", region, url=url)
		fp = FireProx(args, help_str)
		resource_id, proxy_url = fp.create_api(url)
		proxy = AWS_API(proxy_url, api_key=region, api_gateway_id=resource_id)
		return proxy

	def get_fireprox_args(self, command, region, url = None, api_id = None):

		args = {}
		args["access_key"] = self.access_key
		args["secret_access_key"] = self.secret_access_key
		args["url"] = url
		args["command"] = command
		args["region"] = region
		args["api_id"] = api_id
		args["profile_name"] = self.profile_name
		args["session_token"] = self.session_token

		help_str = "Error, inputs cause error."

		return args, help_str

