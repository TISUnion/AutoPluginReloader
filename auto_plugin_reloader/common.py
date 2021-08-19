from typing import TYPE_CHECKING

from mcdreforged.api.types import ServerInterface

if TYPE_CHECKING:
	from auto_plugin_reloader.config import Configure
	from auto_plugin_reloader.reloader import PluginReloader


server_inst = ServerInterface.get_instance().as_plugin_server_interface()
metadata = server_inst.get_self_metadata()
config: 'Configure'
reloader: 'PluginReloader'


def tr(key: str, *args, **kwargs):
	return server_inst.tr('{}.{}'.format(metadata.id, key), *args, **kwargs)


def load_common():
	from auto_plugin_reloader.config import Configure
	from auto_plugin_reloader.reloader import PluginReloader
	global config, reloader
	config = Configure.load()
	reloader = PluginReloader()
