# -*- coding: utf-8 -*-
from Components.config import config, ConfigText, ConfigSubsection
from Components.Network import iNetworkInfo
from Tools.Directories import SCOPE_CONFIG, resolveFilename, pathExists, createDir, fileExists

from stalker import Action, StalkerRequest
from twisted.internet import reactor
from twisted.web.client import Agent, ContentDecoderAgent, GzipDecoder, readBody, PartialDownloadError
from twisted.python.failure import Failure
from twisted.web.http_headers import Headers

import json

from urllib import urlencode
from math import ceil as math_ceil

from Tools.Log import Log

import time
from twisted.python.reflect import isinst

DEFAULT_SERVER = "stalker.server"
DEFAULT_SERVER_ROOT = "/stalker_portal"
DEFAULT_ENDPOINT = "/server/load.php"
MATRIX_ENDPOINT = "/server/matrix.php"

ifaces = iNetworkInfo.getConfiguredInterfaces()
mac = "00:00:00:00:00"
for iface in ifaces.itervalues():
	mac = iface.ethernet.mac
	if mac.startswith("00:09:34"):
		break
DEFAULT_MAC = mac
try:
	from defaults import *
except:
	pass

config.stalker_client = ConfigSubsection()
config.stalker_client.server = ConfigText(default=DEFAULT_SERVER, fixed_size=False)
config.stalker_client.server_root = ConfigText(default=DEFAULT_SERVER_ROOT, fixed_size=False)
config.stalker_client.mac = ConfigText(default=DEFAULT_MAC, fixed_size=False)

class Stalker(object):
	CACHE_DIR_NAME = "stalker"

	def __init__(self):
		self.onLoginSuccess = []
		self.onLoginFailure = []
		self.onGenresReady = []
		self.onGenreServices = []
		self.onAllGenreServices = []
		self.reset()

	def reset(self):
		self._identity = None
		self._isFinishedLoadingChannels = False
		self._isFinishedLoadingGenres = False
		self._isReloading = False
		self._genres = {}
		self._allServices = {}
		self._genreQ = []
		self._genreQcur = None
		self._serviceUrlQ = []
		self._serviceUrlQcur = None

	def _reloadFromDiskCache(self):
		f = resolveFilename(SCOPE_CONFIG, "%s/%s" %(self.CACHE_DIR_NAME, "genres"))
		if fileExists(f):
			Log.w("Reloading services from disk cache")
			data = None
			with open(f) as fdesc:
				data = json.load(fdesc)
				for key, data in data.iteritems():
					genre = StalkerGenre(data)
					self._genres[key] = genre
					self._allServices.update(genre.services)
					Log.i("Loaded genre %s from cache!" %(genre,))
			self._isFinishedLoadingGenres = True
			self._isFinishedLoadingChannels = True
			Log.w("Loaded %s services from cache!" %(len(self._allServices,)))
		else:
			Log.w("No Cache available!")

	def _updateCache(self):
		basepath = resolveFilename(SCOPE_CONFIG, self.CACHE_DIR_NAME)
		if not pathExists(basepath):
			createDir(basepath)
		f = resolveFilename(SCOPE_CONFIG, "%s/%s" %(self.CACHE_DIR_NAME, "genres"))
		data = {}
		for key, genre in self._genres.iteritems():
			data[key] = genre.dict()
		try:
			with open(f, 'w') as fdesc:
				json.dump(data, fdesc)
				Log.w("Disk cache updated (%s services)!" %(len(self._allServices,)))
		except Exception as e:
			Log.w(e)

	def allServices(self):
		return self._allServices.values()

	def genres(self):
		return self._genres.values()

	def service(self, chid):
		return self._allServices.get(chid, None)

	def genreServices(self, genre_id):
		genre = self._genres.get(genre_id, None)
		if genre:
			return genre.services.values()
		return []

	def login(self, identity=None):
		self.reset()
		oldid = self._identity
		self._reloadFromDiskCache()
		if identity:
			self._identity = identity
		else:
			self._identity = oldid
		if self._identity:
			self.handshake(self._onTokenReady)
		else:
			for fnc in self.onLoginFailure:
				fnc()

	def isLoggedIn(self):
		return self._identity and self._identity.token_valid

	def lazyLogin(self):
		if not self.isLoggedIn():
			self.login()
		else:
			self._onProfileReady({"js" : True})

	def _onTokenReady(self, result={}):
		try:
			token = result['js']['token']
			self._identity.token = str(token)
			self._identity.token_valid = True
			self.getProfile(isAuthSecondStep=True, callback=self._onProfileReady)
		except:
			for fnc in self.onLoginFailure:
				fnc()

	def isFinishedLoadingGenres(self):
		return self._isFinishedLoadingGenres

	def isFinishedLoadingChannels(self):
		return self._isFinishedLoadingChannels

	def isReloading(self):
		return self._isReloading

	def _onProfileReady(self, result={}):
		if result:
			for fnc in self.onLoginSuccess:
				fnc()
		else:
			for fnc in self.onLoginFailure:
				fnc()

	def reload(self, lazy=False):
		if not self.isLoggedIn():
			return False
		if self._isFinishedLoadingGenres and lazy:
			if self._isFinishedLoadingChannels:
				Log.w("Channels already loaded!")
				self._loadNextGenre()
			else:
				Log.w("Genres already loaded!")
				self._onGenresReady(None)
			return
		if self.isReloading():
			return
		self._genreQ = []
		self._isFinishedLoadingChannels = False
		self._isFinishedLoadingGenres = False
		self._isReloading = True
		self.getGenres(self._onGenresReady)

	def _getAllServices(self):
		Log.w()
		action = Action.ITV_GET_ALL_CHANNELS
		params = StalkerRequest.getDefaults(action)
		self.call(action, params, self._onAllServicesReady)

	def _onAllServicesReady(self, data={}):
		self._onGenreServicesReady("All", data)

	def _parseGenres(self, data={}):
		if not data:
			self._getAllServices()
			return
		for item in data["js"]:
			genre = StalkerGenre(item)
			if genre.id != "*":
				self._genres[genre.id] = genre
				self._genreQ.append(genre)

	def _onGenresReady(self, result={}):
		self._parseGenres(result)
		self._isFinishedLoadingGenres = True
		for fnc in self.onGenresReady:
			fnc(self.genres())
		self._loadNextGenre()

	def _loadNextGenre(self):
		if self._genreQ:
			self._genreQcur = self._genreQ.pop(0)
			Log.i("Loading services for '%s'" %(self._genreQcur.name,))
			self.getOrderedList(self._genreQcur, self._onGenreServicesReady)
		else:
			self._isFinishedLoadingChannels = True
			self._isReloading = False
			self._updateCache()
			for fnc in self.onAllGenreServices:
				fnc(self._genres)

	def _onGenreServicesReady(self, genre, result={}, isFinished=True):
		Log.d("Got new services for genre %s" %(genre.name,))
		for service in result:
			svc = StalkerService(service)
			genre.services[svc.id] = svc
			self._allServices[svc.id] = svc
		for fnc in self.onGenreServices:
			fnc(genre)
		if isFinished:
			Log.i("%s services total for genre %s" %(len(genre.services), genre.name))
			self._loadNextGenre()

	def _loadNextServiceUrl(self):
		if self._serviceUrlQ:
			self._serviceUrlQcur = self._serviceUrlQ.pop(0)
			Log.i("Loading service url for '%s'" %(self._serviceUrlQcur.name,))
			self.createLink(self._serviceUrlQcur.url, self._onServiceUrlReady)
		else:
			self._loadNextGenre()

	def _onServiceUrlReady(self, data):
		self._serviceUrlQcur.applyTemporaryUrl(data)
		self._loadNextServiceUrl()

	def _getBaseUrl(self):
		server = config.stalker_client.server.value
		if not server.startswith("http"):
			server = "http://%s" %(server,)
		server_root = config.stalker_client.server_root.value
		return "%s%s" %(server, server_root)

	baseurl = property(_getBaseUrl)

	def call(self, action, params=None, callback=None):
		if params is None:
			params = StalkerRequest.getDefaults(action)
		headers = StalkerRequest.getHeaders(self._identity, action, referer=self.baseurl)
		headers["X-User-Agent"] = ["Model: MAG250; Link: WiFi",]
		url = "%s%s?%s" %(self.baseurl, DEFAULT_ENDPOINT, urlencode(params))
		Log.w(url)
		agent = ContentDecoderAgent(Agent(reactor), [('gzip', GzipDecoder)]) #Agent(reactor)

		def bodyCB(body):
			if isinstance(body, Failure):
				if isinstance(body.value, PartialDownloadError):
					body = body.value.response
				else:
					Log.w(body)
					callback(None)
					return
			try:
				result = json.loads(unicode(body))
				Log.d(result)
				callback(result)
			except Exception as e:
				Log.w(body)
				callback(None)

		def bodyErrorCB(error=None):
			Log.w(error)

		def responseCB(response):
			d = readBody(response)
			d.addBoth(bodyCB)

		def errorCB(error=None):
			if(isinstance(error, PartialDownloadError)):
				responseCB(error.response)
				return
			Log.w(error)

		d = agent.request(
			'GET',
			url,
			Headers(headers),
		)
		d.addCallback(responseCB)
		d.addErrback(errorCB)

	def handshake(self, callback=None):
		action = Action.STB_HANDSHAKE
		return self.call(action, callback=callback)

	def getProfile(self, isAuthSecondStep=False, callback=None):
		action = Action.STB_GET_PROFILE
		params = StalkerRequest.getDefaults(action)
		params["auth_second_step"] = isAuthSecondStep
		params["not_valid_token"] = not self._identity.token_valid
		if self._identity.serial_number > 0:
			params["sn"] = self._identity.serial_number
		params["device_id"] = self._identity.device_id
		params["device_id2"] = self._identity.device_id2
		params["signature"] = self._identity.signature
		return self.call(Action.STB_GET_PROFILE, params, callback=callback)

	def doAuth(self):
		action = Action.STB_DO_AUTH
		params = StalkerRequest.getDefaults(action)
		params["login"] = self._identity.login
		params["password"] = self._identity.password
		params["device_id"] = self._identity.device_id
		params["device_id2"] = self._identity.device_id2
		self.call(action)

	def getAllChannels(self, callback=None):
		action = Action.ITV_GET_ALL_CHANNELS
		return self.call(action, callback=callback)

	def getOrderedList(self, genre, callback=None):
		self.begin = time.time()
		genre.currentPage = 1
		genre.lastPage = 1
		genre.channels = []
		genre.callback = callback
		#self.genre = genre

		def doGetCB(result):
			Log.i("Loading the services of %s (page %s/%s) took %s" %(genre.name, genre.currentPage, genre.lastPage, time.time() - self.begin))
			genre.channels.extend(result["js"]["data"])
			if genre.currentPage == 1:
				total_items = float(result["js"]["total_items"])
				max_page_items = float(result["js"]["max_page_items"])
				genre.lastPage = int( math_ceil(total_items / max_page_items ) )
			if genre.currentPage < genre.lastPage:
				genre.currentPage += 1
				doGet(genre, genre.currentPage)
				genre.callback(genre, genre.channels, isFinished=False)
			else:
				genre.callback(genre, genre.channels)

		def doGet(genre, page):
			self.begin = time.time()
			action = Action.ITV_GET_ORDERED_LIST
			params = StalkerRequest.getDefaults(action)
			params["genre"] = genre.id
			params["p"] = page
			self.call(action, params, callback=doGetCB)

		doGet(genre, genre.currentPage)

	def resolveUri(self, uri, callback):
		chid = uri.split("stalker://")[1]
		svc = self.service(chid)
		Log.w(svc)
		if not svc:
			callback(None)
			return
		if svc.http_temp_link:
			def onTempLinkReady(data):
				svc.applyTemporaryUrl(data)
				callback(svc.url)
			self.createLink(svc.url, onTempLinkReady)
		else:
			callback(svc.url)

	def createLink(self, cmd, callback=None):
		action = Action.ITV_CREATE_LINK
		params = StalkerRequest.getDefaults(action)
		params["cmd"] = cmd
		return self.call(action, params, callback=callback)

	def getGenres(self, callback=None):
		action = Action.ITV_GET_GENRES
		return self.call(action, callback=callback)

	def getEpgInfo(self, period, callback=None):
		Log.i()
		action = Action.ITV_GET_EPG_INFO
		params = StalkerRequest.getDefaults(action)
		params["period"] = period
		return self.call(action, params, callback=callback)

	def getEvents(self, curPlayType, eventActiveId, callback=None):
		action = Action.WATCHDOG_GET_EVENTS
		params = StalkerRequest.getDefaults(action)
		params["cur_play_type"] = curPlayType
		params["event_active_id"] = eventActiveId
		return self.call(action, params, callback=callback)

class StalkerBaseService(object):
	def __init__(self, isFolder=False, isPlayable=False):
		self._isFolder = isFolder
		self._isPlayable = isPlayable

	def isFolder(self):
		return self._isFolder

	def isPlayable(self):
		return self._isPlayable

class StalkerService(StalkerBaseService):
	def __init__(self, data):
		StalkerBaseService.__init__(self, isPlayable=True)
		self._name = str(data.get("name", "default")).strip()
		self.id = str(data["id"])
		self.number = int(data.get("number", 0))
		self._cmd = data["cmd"]
		self.applyUrl(data["cmd"])
		self.http_temp_link = data["use_http_tmp_link"]
		self.load_balancing = data["use_load_balancing"]
		self.isOpen = data.get("open", 0) == 1

	def dict(self):
		data = {}
		data["name"] = self._name
		data["id"] = self.id
		data["cmd"] = self._cmd
		data["use_http_tmp_link"] = self.http_temp_link
		data["use_load_balancing"] = self.load_balancing
		data["open"] = self.isOpen
		return data

	def applyUrl(self, cmd):
		cmd = str(cmd).split(" ")
		if len(cmd) > 1:
			self.url = cmd[1]
			self.type = cmd[0]
		else:
			self.url = cmd[0]
			self.type = "ffrt"

	def applyTemporaryUrl(self, data):
		self.applyUrl(data['js']['cmd'])
		Log.d(self.url)
		self.http_temp_link = 1

	def getName(self):
		return self._name

	def setName(self, name):
		self._name = name

	name = property(getName, setName)

	def __str__(self):
		return "~StalkerService - #%s %s : %s : %s : %s (%s, %s)" %(self.number, self.name, self.id, self.type, self.url, self.http_temp_link, self.load_balancing)

class StalkerGenre(StalkerBaseService):
	def __init__(self, data):
		StalkerBaseService.__init__(self, isFolder=True)
		self.id = str(data["id"])
		self.title = str(data["title"]).strip().capitalize()
		self.alias = str(data["alias"]).strip().capitalize()
		self.services = {}
		if "services" in data:
			for key, data in data["services"].iteritems():
				self.services[key] = StalkerService(data)

	def dict(self):
		data = {}
		data["id"] = self.id
		data["title"] = self.title
		data["alias"] = self.alias
		data["services"] = {}
		for key, service in self.services.iteritems():
			data["services"][key] = service.dict()
		return data

	def getName(self):
		return self.title

	def setName(self, name):
		self.title = name

	name = property(getName, setName)

	def __str__(self):
		return "~StalkerGenre - #%s %s / %s (%s services)" %(self.id, self.title, self.alias, len(self.services))

class StalkerEPG(object):
	def __init__(self, data):
		self.id = data
