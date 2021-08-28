from mcdreforged.api.all import *

from auto_plugin_reloader import common
from auto_plugin_reloader.common import tr, metadata

PREFIX = '!!apr'


def show_help(source: CommandSource):
    source.reply(tr('help_message', name=metadata.name, version=metadata.version, prefix=PREFIX))
    show_status(source, True)


def show_status(source: CommandSource, full: bool):
    source.reply(tr('status.0', RText(common.reloader.is_running(), RColor.green if common.reloader.is_running() else RColor.red)))
    if common.reloader.is_running():
        source.reply(tr('status.1', common.reloader.get_pretty_next_detection_time()))
    if full:
        source.reply(tr('status.2', len(common.config.blacklist)))
        for item in common.config.blacklist:
            source.reply('- {}'.format(item))


def set_enable(source: CommandSource, value: bool):
    common.config.enabled = value
    common.config.save()
    common.reloader.on_config_changed()
    source.reply(tr('set_enable.{}'.format(str(value).lower()), value))


def set_interval(source: CommandSource, value: int):
    common.config.detection_interval_sec = value
    common.config.save()
    common.reloader.on_config_changed()
    source.reply(tr('set_interval', value))


def register(server: PluginServerInterface):
    server.register_command(
        Literal(PREFIX).
        requires(lambda src: src.has_permission(common.config.permission), lambda: tr('permission_denied')).
        runs(show_help).
        then(Literal('status').runs(lambda src: show_status(src, False))).
        then(Literal('enable').runs(lambda src: set_enable(src, True))).
        then(Literal('disable').runs(lambda src: set_enable(src, False))).
        then(Literal('set_interval').then(Integer('interval_sec').at_min(1).runs(lambda src, ctx: set_interval(src, ctx['interval_sec']))))
    )
    server.register_help_message(PREFIX, metadata.description)


def on_load(server: PluginServerInterface, old):
    common.load_common()
    common.reloader.on_config_changed()
    common.reloader.start()
    register(server)


def on_unload(server: PluginServerInterface):
    common.reloader.stop()
    common.reloader.join_thread()
