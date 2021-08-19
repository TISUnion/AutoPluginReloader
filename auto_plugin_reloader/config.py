from typing import List

from mcdreforged.api.types import PluginServerInterface, PermissionLevel
from mcdreforged.api.utils import Serializable

from auto_plugin_reloader import common


class Configure(Serializable):
	enabled: bool = True
	permission: int = PermissionLevel.PHYSICAL_SERVER_CONTROL_LEVEL
	detection_interval_sec: float = 10
	reload_delay_sec: float = 1
	blacklist: List[str] = []

	@staticmethod
	def get_psi() -> PluginServerInterface:
		return common.server_inst

	@classmethod
	def load(cls) -> 'Configure':
		return cls.get_psi().load_config_simple(target_class=cls)

	def save(self):
		self.get_psi().save_config_simple(self)
