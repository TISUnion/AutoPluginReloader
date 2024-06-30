from typing import TYPE_CHECKING

from mcdreforged.api.rtext import RTextMCDRTranslation
from mcdreforged.api.types import ServerInterface, PluginServerInterface

if TYPE_CHECKING:
	from auto_plugin_reloader.config import Configuration
	from auto_plugin_reloader.reloader import PluginReloader


server_inst: PluginServerInterface = ServerInterface.psi()
metadata = server_inst.get_self_metadata()
config: 'Configuration'
reloader: 'PluginReloader'


def tr(key: str, *args, **kwargs) -> RTextMCDRTranslation:
	return server_inst.rtr('{}.{}'.format(metadata.id, key), *args, **kwargs)


def load_common():
	from auto_plugin_reloader.config import Configuration
	from auto_plugin_reloader.reloader import PluginReloader
	global config, reloader
	config = Configuration.load()
	reloader = PluginReloader()
