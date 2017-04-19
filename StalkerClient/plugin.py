from enigma import eServiceReference, eUriResolver, StringList
from Components.config import config
from Plugins.Plugin import PluginDescriptor
from Tools.Log import Log

from api import Stalker as un_us_ed
from stalker import Identity
from StalkerChannels import StalkerChannelSelection
from StalkerConfig import StalkerConfig

class StalkerUriResolver(eUriResolver):
	_schemas = ("stalker",)
	instance = None
	def __init__(self):
		Log.w(self._schemas)
		eUriResolver.__init__(self, StringList(self._schemas))

	def resolve(self, service, uri):
		Log.w(uri)
		def onUriReady(uri):
			Log.w()
			if not service.ptrValid():
				return
			if uri:
				service.setResolvedUri(uri, eServiceReference.idDVB)
			else:
				service.failedToResolveUri()
		StalkerChannelSelection.stalker.resolveUri(uri, onUriReady)
		return True

def isBouquetAndOrRoot(csel):
	inBouquet = csel.getMutableList() is not None
	current_root = csel.getRoot()
	current_root_path = current_root and current_root.getPath()
	inBouquetRootList = current_root_path and current_root_path.find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
	Log.w("inBouquet: %s, current_root_path %s, inBouquetRootList %s" %(inBouquet, current_root_path, inBouquetRootList))
	return (inBouquet, inBouquetRootList)

def check_channel(csel):
	inBouquet, inBouquetRootList = isBouquetAndOrRoot(csel)
	return inBouquet and not inBouquetRootList

def check_group(csel):
	inBouquet, inBouquetRootList = isBouquetAndOrRoot(csel)
	return inBouquetRootList

def main_channellist(session, ref, csel, **kwargs):
	Log.i(kwargs)
	if ref:
		session.openWithCallback(onChannelSelected, StalkerChannelSelection, csel)

def onChannelSelected(csel, data, bouquetName=None):
	if bouquetName:
		csel.addBouquet(bouquetName, data)
		return
	if csel.inBouquet() and data:
		if isinstance(data, eServiceReference):
			csel.addServiceToBouquet(csel.getRoot(), service=data)

def main(session, **kwargs):
	session.open(StalkerChannelSelection)

def setup(session, **kwargs):
	session.open(StalkerConfig)

def menu_network(menuid, **kwargs):
	if menuid == "network":
		return [(_("Stalker Streaming Client"), setup, "stalker", 70)]
	else:
		return []

def onLoginSuccess():
	Log.w(StalkerChannelSelection.stalker.reload())
	StalkerChannelSelection.stalker.onLoginSuccess.remove(onLoginSuccess)

def configChanged(unused):
	Log.w("Stalker config changed, reloading")
	login()

def login():
	Log.i("Startin Stalker")
	if not onLoginSuccess in StalkerChannelSelection.stalker.onLoginSuccess:
		StalkerChannelSelection.stalker.onLoginSuccess.append(onLoginSuccess)
	StalkerChannelSelection.stalker.login(Identity(config.stalker_client.mac.value, "en_GB.utf8", "Europe/Berlin"))

def autostart(reason, *args, **kwargs):
	if not reason:
		config.stalker_client.mac.addNotifier(configChanged, initial_call = False, immediate_feedback = False)
		config.stalker_client.server.addNotifier(configChanged, initial_call = False, immediate_feedback = False)
		login()
		StalkerUriResolver.instance = StalkerUriResolver()
		eUriResolver.addResolver(StalkerUriResolver.instance)

def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	return [
		PluginDescriptor(
			name=_("Stalker Autostart"),
			where = PluginDescriptor.WHERE_AUTOSTART,
			fnc=autostart,),
		PluginDescriptor(
			name=_("Stalker Channels"),
			description=_("Watch Stalker Channels"),
			where = [ PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_PLUGINMENU ],
			icon = "plugin.png",
			fnc = main),
		PluginDescriptor(
			name=_("Add Stalker Channel"),
			description=_("Add Stalker Channel"),
			where = PluginDescriptor.WHERE_CHANNEL_CONTEXT_MENU,
			fnc=main_channellist,
			helperfnc=check_channel,
			icon="plugin.png"),
		PluginDescriptor(
			name=_("Add Stalker Group"),
			description=_("Add Stalker Group"),
			where = PluginDescriptor.WHERE_CHANNEL_CONTEXT_MENU,
			fnc=main_channellist,
			helperfnc=check_group,
			icon="plugin.png"),
		PluginDescriptor(
			name=_("Stalker Configuration"),
			description=_("Configure Stalker Middleware Client"),
			where = [ PluginDescriptor.WHERE_EXTENSIONSMENU ],
			icon="plugin.png",
			fnc=setup),
		PluginDescriptor(
			name=_("Stalker Configuration"),
			description=_("Configure Stalker Middleware Client"),
			where = [ PluginDescriptor.WHERE_MENU ],
			icon="plugin.png",
			fnc=menu_network),
		]
