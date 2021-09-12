import os
import time
from threading import Thread, Lock
from typing import List, NamedTuple, Dict, Iterable, Optional

from mcdreforged.api.rtext import *

from auto_plugin_reloader import common
from auto_plugin_reloader.common import tr, metadata, server_inst

ModifyTimeMapping = Dict[str, int]
PLUGIN_FILE_SUFFIXES = ['.py', '.mcdr']


class Difference(NamedTuple):
	file_path: str
	reason: RTextBase


class PluginReloader:
	def __init__(self):
		self.__stop_flag = False
		self.last_detection_time = 0
		self.logger = server_inst.logger
		self.scan_result: ModifyTimeMapping = self.scan_files()
		self.__thread = None  # type: Optional[Thread]
		self.__start_stop_lock = Lock()

	def on_config_changed(self):
		if common.config.enabled:
			self.start()
		else:
			self.stop()

	def is_running(self):
		return self.__thread is not None and self.__thread.is_alive()

	def start(self):
		with self.__start_stop_lock:
			if not self.is_running():
				self.__stop_flag = False
				self.reset_detection_time()
				self.__thread = Thread(name=metadata.name, target=self.thread_loop)
				self.__thread.start()

	def join_thread(self):
		with self.__start_stop_lock:
			thread = self.__thread
		if thread is not None:
			thread.join()

	def stop(self):
		with self.__start_stop_lock:
			self.__stop_flag = True

	# ------------------
	#   Implementation
	# ------------------

	def reset_detection_time(self):
		self.last_detection_time = time.time()

	def get_pretty_next_detection_time(self) -> RTextBase:
		time_next = self.last_detection_time + common.config.detection_interval_sec
		time_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time_next))
		return RText.format('{} ({})', time_text, tr('seconds_later', RText(round(time_next - time.time(), 1), RColor.gold)))

	def thread_loop(self):
		unique_name = '{} @ {}'.format(metadata.name, hex((id(self) >> 16) & (id(self) & 0xFFFF))[2:].rjust(4, '0'))
		self.logger.info('{} started'.format(unique_name))
		while not self.__stop_flag:
			while not self.__stop_flag and time.time() - self.last_detection_time < common.config.detection_interval_sec:
				time.sleep(0.005)
			if self.__stop_flag:
				break
			try:
				self.check()
			except:
				self.logger.exception('Error ticking {}'.format(metadata.name))
				self.stop()
			finally:
				self.reset_detection_time()
		self.logger.info('{} stopped'.format(unique_name))

	@staticmethod
	def scan_files() -> ModifyTimeMapping:
		def has_suffix(text: str, suffixes: Iterable[str]) -> bool:
			return any(map(lambda sfx: text.endswith(sfx), suffixes))

		plugin_directories: List[str] = server_inst.get_mcdr_config()['plugin_directories']
		ret = {}
		for plugin_directory in plugin_directories:
			if os.path.isdir(plugin_directory):
				for file_name in os.listdir(plugin_directory):
					file_path = os.path.join(plugin_directory, file_name)
					if os.path.isfile(file_path) and has_suffix(file_path, PLUGIN_FILE_SUFFIXES) and file_name not in common.config.blacklist:
						ret[file_path] = os.stat(file_path).st_mtime_ns
		return ret

	def check(self):
		new_scan_result = self.scan_files()
		diffs: List[Difference] = []
		for file_path, current_mtime in new_scan_result.items():
			prev_mtime = self.scan_result.get(file_path, None)
			if prev_mtime is None:
				diffs.append(Difference(file_path, tr('file_added')))
			elif prev_mtime != current_mtime:
				diffs.append(Difference(file_path, tr('file_modified')))
		for file_path in self.scan_result.keys():
			if file_path not in new_scan_result:
				diffs.append(Difference(file_path, tr('file_deleted')))

		if len(diffs) > 0:
			time.sleep(common.config.reload_delay_sec)
			if self.__stop_flag:  # just in case
				return
			self.logger.info(tr('triggered.header'))
			for diff in diffs:
				self.logger.info('- {}: {}'.format(diff.file_path, diff.reason))
			self.logger.info(tr('triggered.footer'))
			self.scan_result = self.scan_files()
			server_inst.schedule_task(server_inst.refresh_changed_plugins, block=True)
