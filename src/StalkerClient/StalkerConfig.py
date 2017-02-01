from Components.config import config, getConfigListEntry
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen

from api import Stalker

class StalkerConfig(Screen, ConfigListScreen):
	skin = """
		<screen name="StalkerConfig" position="center,120" size="820,520" title="Stalker Middleware Client Configuration">
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,0" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="210,0" size="200,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,0" zPosition="1" size="200,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="210,0" zPosition="1" size="200,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<eLabel position="10,50" size="800,1" backgroundColor="grey" />
			<widget name="config" position="5,60" size="810,450" scrollbarMode="showOnDemand" enableWrapAround="1"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, [], session=session)
		self.setTitle(_("Stalker Middleware Client Configuration"))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.keyCancel,
			"green": self.keySave,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"ok": self.keySave,
		}, -2)
		self._recreateSetup()

	def _recreateSetup(self):
		lst = [
			getConfigListEntry(_("Stalker Server"), config.stalker_client.server),
			getConfigListEntry(_("API Root"), config.stalker_client.server_root),
			getConfigListEntry(_("Stalker MAC"), config.stalker_client.mac)
		]
		self["config"].list = lst
