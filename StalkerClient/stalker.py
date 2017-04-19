from enigma import HBBTV_USER_AGENT

class Identity(object):
	def __init__(self, mac, lang, time_zone, token=None):
		self.mac = mac
		self.lang = lang
		self.time_zone = time_zone
		self.token = token
		self.token_valid = token != None
		self.login = "id_login"
		self.password = "id_pass"
		self.serial_number = 3
		self.device_id = "id_devid"
		self.device_id2 = "id_devid2"
		self.signature = "id_sig"

class Action(object):
	STB_HANDSHAKE = 0
	STB_GET_PROFILE = 1
	STB_DO_AUTH = 2

	STB_ACTIONS = (	STB_HANDSHAKE, STB_GET_PROFILE, STB_DO_AUTH)

	ITV_GET_ALL_CHANNELS = 0x100
	ITV_GET_ORDERED_LIST = 0x101
	ITV_CREATE_LINK = 0x102
	ITV_GET_GENRES = 0x103
	ITV_GET_EPG_INFO = 0x104
	ITV_GET_SUBSCRIPTION = 0x105

	ITV_ACTIONS = (
		ITV_GET_ALL_CHANNELS,
		ITV_GET_ORDERED_LIST,
		ITV_CREATE_LINK,
		ITV_GET_GENRES,
		ITV_GET_EPG_INFO,
	)

	WATCHDOG_GET_EVENTS = 0x200

	WATCHDOG_ACTIONS = ( WATCHDOG_GET_EVENTS, )

	CMD_MAP = {
		STB_HANDSHAKE : "handshake",
		STB_GET_PROFILE : "get_profile",
		STB_DO_AUTH : "do_auth",
		ITV_GET_ALL_CHANNELS : "get_all_channels",
		ITV_GET_ORDERED_LIST : "get_ordered_list",
		ITV_CREATE_LINK : "create_link",
		ITV_GET_GENRES : "get_genres",
		ITV_GET_EPG_INFO : "get_epg_info",
		WATCHDOG_GET_EVENTS : "get_events",
	}

class ITV(object):
	@staticmethod
	def getAllChannelsDefaults():
		return {}

	@staticmethod
	def getOrderedListDefaults():
		return {
			"fav" : 0, #required
			"sortby" : "number", #required
			"p" : 0, #optional
		}

	@staticmethod
	def getCreateLinkDefaults():
		return {
			"cmd" : "", #required
			"forced_storage" : "undefined", #optional
			"disable_ad" : 0, #optional
		}

	@staticmethod
	def getGenreDefaults():
		return {}

	@staticmethod
	def getEpgInfoDefaults():
		return {"period" : 24}

	@staticmethod
	def getDefaults(action):
		if action == Action.ITV_GET_ALL_CHANNELS:
			return ITV.getAllChannelsDefaults()
		elif action == Action.ITV_GET_ORDERED_LIST:
			return ITV.getOrderedListDefaults()
		elif action == Action.ITV_CREATE_LINK:
			return ITV.getCreateLinkDefaults()
		elif action == Action.ITV_GET_GENRES:
			return ITV.getGenreDefaults()
		elif action == Action.ITV_GET_EPG_INFO:
			return ITV.getEpgInfoDefaults()

class STB(object):
	@staticmethod
	def getHanshakeDefaults():
		return { "token" : "" } #otpional

	@staticmethod
	def getProfileDefaults():
		return {
			"stb_type" : "MAG250",
			"ver" : "ImageDescription: 0.2.16-250; " \
					"ImageDate: 18 Mar 2013 19:56:53 GMT+0200; " \
					"PORTAL version: 4.9.9; " \
					"API Version: JS API version: 328; " \
					"STB API version: 134; " \
					"Player Engine version: 0x566",
			"device_id" : "", #optional
			"device_id2" : "", #optional
			"signature" : "", #optional
			"not_valid_token" : False, #required
			"auth_second_step" : False, #required
			"hd" : True, #required
			"num_banks" : 1, #required
			"image_version" : 216, #required
			"hw_version" : "1.7-BD-00", #required
		}

	@staticmethod
	def getAuthDefaults():
		return {
			"password" : "", #required
			"device_id" : "", #optional
			"device_id2" : "", #optional
		}

	@staticmethod
	def getDefaults(action):
		if action == Action.STB_HANDSHAKE:
			return STB.getHanshakeDefaults()
		elif action == Action.STB_GET_PROFILE:
			return STB.getProfileDefaults()
		elif action == Action.STB_DO_AUTH:
			return STB.getAuthDefaults()

class Watchdog(object):
	@staticmethod
	def getEventDefaults():
		return {
			"init" : False, # required
			"cur_play_type" : 0,  #required
			"event_active_id": 0, #required
		}

	@staticmethod
	def getDefaults(action):
		if action == Action.WATCHDOG_GET_EVENTS:
			return Watchdog.getEventDefaults()

class StalkerRequest(object):
	USER_AGENT = HBBTV_USER_AGENT

	@staticmethod
	def getHeaders(identity, action, referer=""):
		headers = {
			"Cookie" : ["mac=%s; stb_lang=%s, timezone=%s" % (identity.mac, identity.lang, identity.time_zone),],
			"User-agent" : [StalkerRequest.USER_AGENT,],
		}
		if action != Action.STB_HANDSHAKE:
			headers["Authorization"] = ["Bearer %s" % (identity.token),]
		if action == Action.ITV_CREATE_LINK:
			headers["Referer"] = [referer]
		return headers # Headers(headers)

	@staticmethod
	def getParams(action, params):
		request_type = ""
		if action in Action.STB_ACTIONS:
			request_type = "stb"
		elif action in Action.ITV_ACTIONS:
			request_type = "itv"
		elif action in Action.WATCHDOG_ACTIONS:
			request_type = "watchdog"

		params["type"] = request_type
		params["action"] = Action.CMD_MAP.get(action)
		return params

	@staticmethod
	def getDefaults(action):
		if action in Action.STB_ACTIONS:
			return StalkerRequest.getParams(action, STB.getDefaults(action))
		elif action in Action.ITV_ACTIONS:
			return StalkerRequest.getParams(action, ITV.getDefaults(action))
		elif action in Action.WATCHDOG_ACTIONS:
			return StalkerRequest.getParams(action, Watchdog.getDefaults(action))
