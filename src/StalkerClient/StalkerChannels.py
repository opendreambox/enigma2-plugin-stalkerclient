from enigma import eServiceReference, StringMap

from Screens.Screen import Screen
from Screens.MoviePlayer import MoviePlayer
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Label import Label

from api import Stalker
from stalker import StalkerRequest

from Tools.Log import Log
from Screens.Toast import Toast

class StalkerChannelSelection(Screen):
	MODE_DEFAULT = 0
	MODE_ADD_SERVICE = 1
	MODE_ADD_GROUP = 2

	stalker = Stalker()

	skin = """<screen name="StalkerChannelSelection" position="center,120" size="920,420">
		<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="200,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="200,40" alphatest="on" />
		<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
		<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
		<widget name="key_yellow" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1"  shadowColor="black" shadowOffset="-2,-2" />
		<widget name="key_blue" position="610,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
		<widget source="global.CurrentTime" render="Label" position="830,12" size="60,25" font="Regular;22" halign="right" backgroundColor="background" shadowColor="black" shadowOffset="-2,-2" transparent="1">
			<convert type="ClockToText">Default</convert>
		</widget>
		<widget source="list" render="Listbox" position="10,58" size="900,360" backgroundColor="background">
			<convert type="TemplatedMultiContent">
				{"template": [ MultiContentEntryText(pos=(10,4),size=(580,22),flags=RT_HALIGN_LEFT,text=1) ],
				"fonts": [gFont("Regular",20)],
				"itemHeight": 30
				}
			</convert>
		</widget>
		<eLabel position="10,50" size="900,1" backgroundColor="grey" />
	</screen>
	"""

	def __init__(self, session, csel=None, parent=None):
		Screen.__init__(self, session, parent=parent, windowTitle=_("Stalker Services"))
		self._items = []
		self._list = List(self.items, enableWrapAround=True)

		inBouquet = False
		inBouquetRootList = False
		if csel:
			inBouquet = csel.getMutableList() is not None
			current_root = csel.getRoot()
			current_root_path = current_root and current_root.getPath()
			inBouquetRootList = current_root_path and current_root_path.find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK

		self._mode = self.MODE_DEFAULT
		if inBouquet:
			self._mode = self.MODE_ADD_GROUP if inBouquetRootList else self.MODE_ADD_SERVICE
		self._csel = csel

		self["key_red"] = Label("")
		self["key_green"] = Label("")
		self["key_yellow"] = Label(_("Reload"))
		self["key_blue"] = Label(_("Genres"))
		self["list"] = self._list

		self["actions"] = ActionMap(["ListboxActions", "OkCancelActions", "ColorActions"],
		{
			"ok" : self.ok,
			"cancel" : self.cancel,
			"yellow" : self._reload,
			"blue" : self.showGenres,
		});

		self._connectToStalker()
		self.onClose.append(self._disconnectFromStalker)
		self.stalker.lazyLogin()

	def close(self, *args):
		if self._mode != self.MODE_DEFAULT and not args:
			Screen.close(self, self._csel, None, *args)
		else:
			Screen.close(self, *args);

	def _connectToStalker(self):
		self.stalker.onLoginSuccess.append(self.onLogin)
		self.stalker.onLoginFailure.append(self.onLoginFailure)
		self.stalker.onGenresReady.append(self.onGenresReady)
		self.stalker.onGenreServices.append(self.onGenreServices)
		self.stalker.onAllGenreServices.append(self.onAllGenreServices)

	def _disconnectFromStalker(self):
		self.stalker.onLoginSuccess.remove(self.onLogin)
		self.stalker.onGenresReady.remove(self.onGenresReady)
		self.stalker.onGenreServices.remove(self.onGenreServices)
		self.stalker.onAllGenreServices.remove(self.onAllGenreServices)

	def _buildItem(self, item):
		name = item.name
		if item.isFolder():
			cnt = len(item.services) or _("loading ...")
			if cnt:
				name = "%s (%s)" %(item.name, cnt)
		entry = (item.id, name, item)
		return entry

	def _reload(self):
		self.stalker.reload(lazy=False)

	def showGenres(self):
		self._items = []
		for genre in self.stalker.genres():
			self._items.append(self._buildItem(genre))
		self._sortAndApply()

	def cancel(self):
		self.close()

	def ok(self):
		if not self._items:
			return
		current = self._list.current
		if current:
			service = current[-1]
			if service.isPlayable():
				ref = self._serviceToRef(service)
				if self._mode == self.MODE_ADD_SERVICE:
					self.close(self._csel, ref)
					return
				self.session.open(MoviePlayer, ref, streamMode=True, askBeforeLeaving=False)
				self.hide()
			elif service.isFolder():
				if self._mode == self.MODE_ADD_GROUP:
					refs = []
					for svc in service.services.itervalues():
						refs.append(self._serviceToRef(svc))
					self.close(self._csel, refs, service.name)
					return
				self._loadServicesForGenre(service.id)

	def _serviceToRef(self, service):
		ref = eServiceReference(eServiceReference.idURI, 0, "stalker://%s" %(service.id,))
		ref.setData(0, 1)
		ref.setData(1, int(service.number))
		ref.setName(service.name)
		return ref

	def onGenresReady(self, unused):
		self.showGenres()

	def onAllGenreServices(self, genres):
		for genre in self.stalker.genres():
			Log.i("%s (%s)" % (genre.title, genre.id))
		self.session.toastManager.showToast("Got %s services in %s genres total" % (len(self.stalker.allServices()), len(genres),), Toast.DURATION_SHORT)
		self.showGenres()

	def onLogin(self):
		Log.w("Reloading stalker services")
		self.stalker.reload(lazy=True)

	def onLoginFailure(self):
		self.session.toastManager.showToast(_("Stalker login failed!"), Toast.DURATION_SHORT)

	def onGenreServices(self, genre):
		Log.d("%s - got %s services" % (genre.name, len(genre.services),))
		if not self._items or self._items[0][-1].isFolder():
			self.showGenres()

	def _loadServicesForGenre(self, genre_id):
		services = self.stalker.genreServices(genre_id)
		if services:
			self._items = []
			for service in self.stalker.genreServices(genre_id):
				self._items.append(self._buildItem(service))
			self._sortAndApply()

	def _sortAndApply(self):
		self._items = sorted(self._items, key=lambda service: service[-1].name)
		index = self._list.index
		self._list.list = self._items
		if len(self._items) > index:
			self._list.index = index
