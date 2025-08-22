import contextlib
import dataclasses
import enum
import os
import threading
import time
from pathlib import Path
from threading import Thread, Lock
from typing import List, Dict, Iterable, Optional, Set

from mcdreforged.api.rtext import *
from mcdreforged.api.types import PluginType

from auto_plugin_reloader import common
from auto_plugin_reloader.common import tr, metadata, server_inst

PLUGIN_FILE_SUFFIXES = ['.py', '.mcdr', '.pyz']


@dataclasses.dataclass(frozen=True)
class PluginFileInfo:
	plugin_id: Optional[str]
	path: Path
	mtime: Optional[int]


@dataclasses.dataclass(frozen=True)
class ScanResult:
	files: Dict[Path, PluginFileInfo] = dataclasses.field(default_factory=dict)
	plugin_files: Dict[str, PluginFileInfo] = dataclasses.field(default_factory=dict)


class DiffReason(enum.Enum):
	file_added = enum.auto()
	file_modified = enum.auto()
	file_deleted = enum.auto()


@dataclasses.dataclass(frozen=True)
class Difference:
	file_path: Path
	reason: DiffReason
	plugin_id: Optional[str]


class PluginReloader:
	def __init__(self):
		self.__stop_flag = threading.Event()
		self.last_detection_time = 0
		self.logger = server_inst.logger
		self.scan_result: ScanResult = self.__scan_files()
		self.__thread: Optional[Thread] = None
		self.__start_stop_lock = Lock()

	def on_config_changed(self):
		if common.config.enabled:
			self.start()
		else:
			self.stop()

	@property
	def unique_hex(self) -> str:
		return hex((id(self) >> 16) & (id(self) & 0xFFFF))[2:].rjust(4, '0')

	@property
	def unique_name(self) -> str:
		return '{} @ {}'.format(metadata.name, self.unique_hex)

	def is_running(self):
		return self.__thread is not None and self.__thread.is_alive()

	def start(self):
		with self.__start_stop_lock:
			if not self.is_running():
				self.__stop_flag.clear()
				self.__reset_detection_time()
				self.__thread = Thread(name='APR@{}'.format(self.unique_hex), target=self.thread_loop)
				self.__thread.start()

	def join_thread(self):
		with self.__start_stop_lock:
			thread = self.__thread
		if thread is not None:
			thread.join()

	def stop(self):
		self.__stop_flag.set()

	# ------------------
	#   Implementation
	# ------------------

	def __reset_detection_time(self):
		self.last_detection_time = time.time()

	def get_pretty_next_detection_time(self) -> RTextBase:
		time_next = self.last_detection_time + common.config.detection_interval_sec
		time_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time_next))
		return RText.format('{} ({})', time_text, tr('seconds_later', RText(round(time_next - time.time(), 1), RColor.gold)))

	def thread_loop(self):
		self.logger.info('{} started'.format(self.unique_name))

		while True:
			next_detection_time = self.last_detection_time + common.config.detection_interval_sec
			time_to_wait = max(0.0, next_detection_time - time.time())
			if self.__stop_flag.wait(time_to_wait):
				break

			try:
				self.__check_and_reload_once()
			except Exception:
				self.logger.exception('Error ticking {}'.format(metadata.name))
				self.stop()
			finally:
				self.__reset_detection_time()

		self.logger.info('{} stopped'.format(self.unique_name))

	def __scan_files(self) -> ScanResult:
		self.logger.debug('Scan file start')
		start_time = time.time()

		def has_suffix(text: str, suffixes: Iterable[str]) -> bool:
			return any(map(lambda sfx: text.endswith(sfx), suffixes))

		def try_get_mtime(p: Path) -> Optional[int]:
			try:
				return p.stat().st_mtime_ns
			except OSError:
				return None

		result = ScanResult()
		plugin_paths: Set[Path] = set()
		for pid in server_inst.get_plugin_list():
			path = server_inst.get_plugin_file_path(pid)
			pfmt = server_inst.get_plugin_type(pid)
			if path is not None and pfmt in [PluginType.solo, PluginType.packed]:
				path = Path(path).absolute()
				pfi = PluginFileInfo(plugin_id=pid, path=path, mtime=try_get_mtime(path))
				result.files[path] = pfi
				result.plugin_files[pid] = pfi
				plugin_paths.add(path)

		plugin_directories: List[str] = server_inst.get_mcdr_config()['plugin_directories']
		for plugin_directory in map(Path, plugin_directories):
			try:
				files = os.listdir(plugin_directory)
			except OSError as e:
				if not isinstance(e, FileNotFoundError):
					self.logger.warning('Skipping invalid plugin directory {!r}: {}'.format(plugin_directory, e))
				continue

			for file_name in files:
				path = (plugin_directory / file_name).absolute()
				if path in plugin_paths:
					continue
				try:
					if path.is_file() and has_suffix(file_name, PLUGIN_FILE_SUFFIXES) and file_name not in common.config.blacklist:
						mtime = path.stat().st_mtime_ns
						result.files[path] = PluginFileInfo(plugin_id=None, path=path, mtime=mtime)
				except OSError as e:
					self.logger.warning('Check file {!r} failed: {}'.format(plugin_directory, e))

		self.logger.debug('Scan file end, cost {:.2f}s'.format(time.time() - start_time))
		return result

	@dataclasses.dataclass(frozen=True)
	class _CheckOnceResult:
		scan_result: ScanResult
		diffs: List[Difference] = dataclasses.field(default_factory=list)
		to_load: List[Path] = dataclasses.field(default_factory=list)   # paths
		to_reload: List[str] = dataclasses.field(default_factory=list)  # plugin id
		to_unload: List[str] = dataclasses.field(default_factory=list)  # plugin id

	def __scan_and_check(self) -> _CheckOnceResult:
		new_scan_result = self.__scan_files()
		cor = self._CheckOnceResult(scan_result=new_scan_result)

		for pid, pfi in self.scan_result.plugin_files.items():
			if (new_pfi := new_scan_result.plugin_files.get(pid)) is None:
				continue
			# the plugin exists in both 2 scans
			# reload if mtime changes, and mcdr also says that it has changes
			# if pid == 'advanced_calculator':
			# 	self.logger.info('OLD {}'.format(pfi))
			# 	self.logger.info('NEW {}'.format(new_pfi))
			if pfi.mtime != new_pfi.mtime and server_inst.is_plugin_file_changed(pid) is True:
				if new_pfi.mtime is None:
					cor.diffs.append(Difference(pfi.path, DiffReason.file_deleted, pid))
					cor.to_unload.append(pid)
				else:
					cor.diffs.append(Difference(pfi.path, DiffReason.file_modified, pid))
					cor.to_reload.append(pid)

		for path, new_pfi in new_scan_result.files.items():
			# newly found, not loaded, plugin file
			if new_pfi.plugin_id is None and ((old_pfi := self.scan_result.files.get(path)) is None or new_pfi.mtime != old_pfi.mtime):
				cor.diffs.append(Difference(path, DiffReason.file_added, None))
				cor.to_load.append(path)

		return cor

	def __check_and_reload_once(self):
		# first check
		check_result = self.__scan_and_check()
		if len(check_result.diffs) == 0:
			self.scan_result = check_result.scan_result
			return
		self.logger.info('Found {} plugin file changes'.format(len(check_result.diffs)))

		# wait for a while before the double check
		if self.__stop_flag.wait(common.config.reload_delay_sec):
			return

		# second check
		check_result = self.__scan_and_check()
		self.scan_result = check_result.scan_result
		if len(check_result.diffs) == 0:
			self.logger.info('Got no diff in second check')
			return

		self.logger.info(tr('triggered.header'))
		for diff in check_result.diffs:
			path = diff.file_path
			with contextlib.suppress(ValueError):
				path = path.relative_to(Path('.').absolute())
			msg = '- {}: {}'.format(path, tr(diff.reason.name))
			if diff.plugin_id:
				msg += ' (id={})'.format(diff.plugin_id)
			self.logger.info(msg)
		self.logger.info(tr('triggered.footer'))

		def do_auto_reload():
			try:
				server_inst.manipulate_plugins(
					load=[str(p) for p in check_result.to_load],
					reload=check_result.to_reload,
					unload=check_result.to_unload,
				)
			except Exception:
				self.logger.exception('Auto plugin reload failed')

		holder = Thread(name='OperationHolder', daemon=True, target=lambda: server_inst.schedule_task(do_auto_reload, block=True))
		holder.start()
		while holder.is_alive() and not self.__stop_flag.is_set():  # stop waiting after being stopped
			holder.join(timeout=0.01)
