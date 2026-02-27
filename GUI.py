# ======================== 导入模块 ========================
import sys
import os
import re
import subprocess
import time
import threading
import queue
import random
import configparser
import json
from pathlib import Path
from PIL import Image, ImageEnhance
from datetime import datetime

# PyQt5模块
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel

# 系统托盘
import pystray
from pystray import MenuItem as item
from PIL import Image as PILImage

# ======================== 常量定义 ========================
WINDOW_TITLE = "哔哩哔哩视频批量下载器"
WINDOW_SIZE = (1000, 700)

# 图标和图片路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICO_FILE = os.path.join(BASE_DIR, "icon.ico")
ADD_ICON_PATH = os.path.join(BASE_DIR, 'image', 'add.png')
DELETE_ICON_PATH = os.path.join(BASE_DIR, 'image', 'delete.png')
BACK_ICON_PATH = os.path.join(BASE_DIR, 'image', 'break.png')

# 文档路径
ABOUT_HTML_PATH = os.path.join(BASE_DIR, 'doc', 'about.html')
DOWNLOADER_EXE_PATH = os.path.join(BASE_DIR, "you-get-ourpet.exe")

# FFmpeg相关配置
FFMPEG_WIN_NAME = "ffmpeg.exe"
FFMPEG_UNIX_NAME = "ffmpeg"
FFMPEG_PATH = None

# 配置文件路径
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")


# ======================== 工具类和函数 ========================
def get_ffmpeg_path():
	"""获取ffmpeg路径"""
	global FFMPEG_PATH
	script_dir = os.path.dirname(os.path.abspath(__file__))
	
	if sys.platform == "win32":
		ffmpeg_filename = FFMPEG_WIN_NAME
	else:
		ffmpeg_filename = FFMPEG_UNIX_NAME
	
	FFMPEG_PATH = os.path.join(script_dir, ffmpeg_filename)
	return FFMPEG_PATH


class ConfigManager:
	"""配置管理器"""
	
	def __init__(self):
		self.config_file = 'config.ini'
		self.encoding = 'utf-8'
		self.config = configparser.ConfigParser()
		
		if not os.path.exists(self.config_file):
			print("配置文件不存在，尝试初始化...")
			self.config['path'] = {
				'downloads': os.path.join(os.path.expanduser('~'), 'Desktop', 'BilibiliDownloads').replace('\\', '/'),
				'logs': 'logs'
			}
			self.config['info'] = {
				'encoding': 'utf-8'
			}
			with open(self.config_file, 'w', encoding=self.encoding) as f:
				self.config.write(f)
		
		try:
			self.config.read(self.config_file, encoding=self.encoding)
		except Exception as e:
			print(f"读取配置文件失败: {e}")
			self.config['path'] = {
				'downloads': os.path.join(os.path.expanduser('~'), 'Desktop', 'BilibiliDownloads').replace('\\', '/'),
				'logs': 'logs'
			}
			self.config['info'] = {
				'encoding': 'utf-8'
			}
			with open(self.config_file, 'w', encoding=self.encoding) as f:
				self.config.write(f)
			self.config.read(self.config_file, encoding=self.encoding)
	
	def get(self, section, option, fallback=None):
		try:
			return self.config.get(section, option)
		except:
			return fallback


class SettingsManager:
	"""设置管理器"""
	
	def __init__(self):
		# 确保配置目录存在
		os.makedirs(CONFIG_DIR, exist_ok=True)
		
		# 默认设置
		self.default_settings = {
			"ffmpeg_path": get_ffmpeg_path(),
			"downloader_path": DOWNLOADER_EXE_PATH,
			"font_size": 11,
			"theme": "light",  # light/dark
			"auto_start": False,
			"max_downloads": 3,
			"download_path": os.path.join(os.path.expanduser('~'), 'Desktop', 'BilibiliDownloads')
		}
		
		self.load_settings()
	
	def load_settings(self):
		"""加载设置"""
		if os.path.exists(CONFIG_FILE):
			try:
				with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
					self.settings = json.load(f)
				# 合并默认设置，确保所有键都存在
				for key, value in self.default_settings.items():
					if key not in self.settings:
						self.settings[key] = value
			except:
				self.settings = self.default_settings.copy()
		else:
			self.settings = self.default_settings.copy()
			self.save_settings()
	
	def save_settings(self):
		"""保存设置"""
		try:
			with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
				json.dump(self.settings, f, indent=2, ensure_ascii=False)
		except Exception as e:
			print(f"保存设置失败: {e}")
	
	def get(self, key, default=None):
		"""获取设置值"""
		return self.settings.get(key, default)
	
	def set(self, key, value):
		"""设置值"""
		self.settings[key] = value
		self.save_settings()


class Logger:
	"""日志记录器"""
	
	def __init__(self):
		self.config_mgr = ConfigManager()
		self.log_dir = self.config_mgr.get('path', 'logs', 'logs')
		self.encoding = self.config_mgr.get('info', 'encoding', 'utf-8')
		self.is_closed = False
		
		# 确保日志目录存在
		self.mkdir(self.log_dir)
	
	def mkdir(self, path):
		"""创建目录"""
		try:
			path = os.path.normpath(str(path))
			os.makedirs(path, exist_ok=True)
			if os.path.exists(path) and os.path.isdir(path):
				print(f"目录创建成功: {path}")
				self.log("SYSTEM", f"创建目录成功: {path}")
				return True
			else:
				print(f"目录创建失败: {path}")
				return False
		except Exception as e:
			print(f"创建目录失败 {path}: {e}")
			return False
	
	def get_ip(self):
		return random.randint(1000, 9999)
	
	def log(self, log_head, message, log_ip=None, log_id=None, log_time=None):
		"""记录日志"""
		if self.is_closed:
			return
		
		if log_ip is None:
			log_ip = self.get_ip()
		if log_id is None:
			log_id = int(time.time() * 1000000)
		if log_time is None:
			log_time = time.strftime('%Y.%m.%d %H:%M:%S')
		log_entry = f'[{log_head}]\n\ttime:{log_time}\n\t\tid:{log_id}\n\t\t\tip:{log_ip}\n\t\t\t\t{message}\n\n'
		try:
			log_file = os.path.join(self.log_dir, f"{time.strftime('%Y-%m-%d')}.log")
			with open(log_file, 'a', encoding=self.encoding) as f:
				f.write(log_entry)
			print(f"[{log_head}] {message}")
		except Exception as e:
			if not self.is_closed:
				print(f"写入日志失败: {e}")
	
	def close(self):
		self.is_closed = True


class DownloadWorker(QThread):
	"""下载工作线程"""
	progress_signal = pyqtSignal(int, str)  # 进度, 状态信息
	log_signal = pyqtSignal(str)
	finished_signal = pyqtSignal(bool, str)
	
	def __init__(self, url, output_path, settings):
		super().__init__()
		self.url = url
		self.output_path = output_path
		self.settings = settings
		self.is_running = True
	
	def run(self):
		try:
			# 处理URL
			processed_url = self.process_url(self.url)
			if not processed_url:
				self.finished_signal.emit(False, "无效的B站链接")
				return
			
			# 检查下载器路径
			downloader_path = self.settings.get("downloader_path", DOWNLOADER_EXE_PATH)
			if not os.path.exists(downloader_path):
				self.finished_signal.emit(False, f"找不到下载器: {downloader_path}")
				return
			
			# 准备命令
			output = f'"{self.output_path}"'
			cmd = f'"{downloader_path}" -o {output} "{processed_url}"'
			
			self.log_signal.emit(f"开始下载: {processed_url}")
			self.progress_signal.emit(0, "正在启动下载...")
			
			# 执行下载命令并实时捕获输出
			process = subprocess.Popen(
				cmd,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				universal_newlines=True,
				bufsize=1,
				encoding='utf-8',
				errors='ignore'
			)
			
			# 解析进度
			last_progress = 0
			file_part = 1
			
			for line in iter(process.stdout.readline, ''):
				if not self.is_running:
					process.terminate()
					break
				
				line = line.strip()
				if line:
					self.log_signal.emit(line)
					
					# 解析进度信息
					progress = self.parse_progress(line)
					if progress is not None and progress > last_progress:
						if "[2/2]" in line and file_part == 1:
							file_part = 2
							if last_progress < 50:
								self.progress_signal.emit(50, f"下载第一部分完成")
								last_progress = 50
						
						if file_part == 1:
							actual_progress = progress / 2
						else:
							actual_progress = 50 + (progress / 2)
						
						if actual_progress > last_progress:
							self.progress_signal.emit(int(actual_progress), f"下载进度: {int(actual_progress)}%")
							last_progress = actual_progress
			
			process.wait()
			
			if process.returncode == 0:
				self.progress_signal.emit(100, "下载完成")
				self.finished_signal.emit(True, f"下载成功: {self.url}")
			else:
				self.finished_signal.emit(False, f"下载失败: {self.url}")
		
		except Exception as e:
			self.finished_signal.emit(False, f"下载出错: {str(e)}")
	
	def process_url(self, url):
		"""处理URL"""
		if not isinstance(url, str) or not url.strip():
			return None
		
		url = url.strip()
		
		# 检查是否已经是完整URL
		if re.search(r'https?://(www\.)?bilibili\.com/video/', url.lower()):
			return url
		
		# 检查BV号
		bv_match = re.search(r'(BV[0-9A-Za-z]{10})', url, re.IGNORECASE)
		if bv_match:
			return f"https://www.bilibili.com/video/{bv_match.group(1)}"
		
		# 检查AV号
		av_match = re.search(r'[Aa][Vv](\d+)', url)
		if av_match:
			av_num = av_match.group(1)
			if av_num.isdigit() and len(av_num) >= 5:
				return f"https://www.bilibili.com/video/av{av_num}"
		
		return None
	
	def parse_progress(self, line):
		"""解析进度信息"""
		match = re.search(r'(\d+\.?\d*)%', line)
		if match:
			try:
				return float(match.group(1))
			except:
				pass
		return None
	
	def stop(self):
		"""停止下载"""
		self.is_running = False


# ======================== 系统托盘管理器 ========================
class SystemTrayManager:
	"""系统托盘管理器"""
	
	def __init__(self, main_window):
		self.main_window = main_window
		self.tray_icon = None
		self.tray_thread = None
		self.is_running = False
	
	def start(self):
		"""启动系统托盘"""
		try:
			# 在新线程中运行系统托盘
			self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
			self.tray_thread.start()
			return True
		except Exception as e:
			print(f"启动系统托盘失败: {e}")
			return False
	
	def _run_tray(self):
		"""运行系统托盘"""
		try:
			# 加载图标
			if os.path.exists(ICO_FILE):
				icon = PILImage.open(ICO_FILE)
			else:
				# 创建默认图标
				icon = PILImage.new('RGB', (64, 64), color=(51, 153, 255))
			
			# 创建菜单
			menu = (
				item('显示窗口', self._on_show_window),
				item('关于我们', self._on_about),
				item('设置', self._on_settings),
				item('退出', self._on_exit)
			)
			
			# 创建系统托盘图标
			self.tray_icon = pystray.Icon(
				"bilibili_downloader",
				icon,
				"哔哩哔哩下载器",
				menu
			)
			
			self.is_running = True
			self.tray_icon.run()
		
		except Exception as e:
			print(f"系统托盘运行失败: {e}")
	
	def _on_show_window(self, icon, item):
		"""显示窗口菜单点击"""
		QMetaObject.invokeMethod(self.main_window, "show_window", Qt.QueuedConnection)
	
	def _on_about(self, icon, item):
		"""关于我们菜单点击"""
		QMetaObject.invokeMethod(self.main_window, "show_about", Qt.QueuedConnection)
	
	def _on_settings(self, icon, item):
		"""设置菜单点击"""
		QMetaObject.invokeMethod(self.main_window, "open_settings_window", Qt.QueuedConnection)
	
	def _on_exit(self, icon, item):
		"""退出菜单点击"""
		QMetaObject.invokeMethod(self.main_window, "close_application", Qt.QueuedConnection)
	
	def stop(self):
		"""停止系统托盘"""
		if self.tray_icon and self.is_running:
			try:
				self.tray_icon.stop()
				self.is_running = False
			except:
				pass


# ======================== 主窗口类 ========================
class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.logger = Logger()
		self.settings = SettingsManager()
		self.download_workers = []
		self.url_widgets = []
		self.is_downloading = False
		
		# 系统托盘
		self.tray_manager = SystemTrayManager(self)
		
		# 窗口引用
		self.about_window = None
		self.settings_window = None
		self.merge_window = None
		self.m4s_window = None
		
		self.init_ui()
		self.tray_manager.start()
	
	def init_ui(self):
		"""初始化UI"""
		self.setWindowTitle(WINDOW_TITLE)
		self.setGeometry(100, 100, 1000, 700)
		
		# 设置窗口图标
		if os.path.exists(ICO_FILE):
			self.setWindowIcon(QIcon(ICO_FILE))
		
		# 应用设置的主题
		self.apply_theme()
		
		# 创建中央部件
		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		
		# 主布局
		main_layout = QVBoxLayout(central_widget)
		main_layout.setContentsMargins(15, 15, 15, 15)
		main_layout.setSpacing(10)
		
		# 标题栏
		title_bar = QWidget()
		title_layout = QHBoxLayout(title_bar)
		title_layout.setContentsMargins(0, 0, 0, 0)
		
		# 返回按钮
		back_icon = self.load_icon(BACK_ICON_PATH, (24, 24))
		self.back_btn = QPushButton()
		if back_icon:
			self.back_btn.setIcon(back_icon)
		else:
			self.back_btn.setText("←")
		self.back_btn.setFixedSize(40, 40)
		self.back_btn.setObjectName("backBtn")
		self.back_btn.clicked.connect(self.hide_to_tray)
		
		# 标题
		title_label = QLabel('哔哩哔哩视频批量下载器')
		title_label.setObjectName("titleLabel")
		
		# 添加按钮
		add_icon = self.load_icon(ADD_ICON_PATH, (24, 24))
		self.add_btn = QPushButton()
		if add_icon:
			self.add_btn.setIcon(add_icon)
		else:
			self.add_btn.setText("+")
		self.add_btn.setFixedSize(40, 40)
		self.add_btn.setObjectName("addBtn")
		self.add_btn.clicked.connect(self.add_url_widget)
		
		title_layout.addWidget(self.back_btn)
		title_layout.addWidget(title_label, 1)
		title_layout.addWidget(self.add_btn)
		
		# URL输入区域
		url_container = QWidget()
		url_layout = QVBoxLayout(url_container)
		url_layout.setContentsMargins(0, 0, 0, 0)
		
		# 滚动区域
		self.url_scroll_area = QScrollArea()
		self.url_scroll_area.setWidgetResizable(True)
		self.url_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		
		self.url_scroll_widget = QWidget()
		self.url_scroll_layout = QVBoxLayout(self.url_scroll_widget)
		self.url_scroll_layout.setSpacing(8)
		
		self.url_scroll_area.setWidget(self.url_scroll_widget)
		url_layout.addWidget(self.url_scroll_area)
		
		# 添加第一个URL输入框
		self.add_url_widget(initial=True)
		
		# 输出目录区域
		output_widget = QWidget()
		output_layout = QHBoxLayout(output_widget)
		output_layout.setContentsMargins(0, 0, 0, 0)
		
		output_label = QLabel('输出目录:')
		output_label.setFixedWidth(80)
		
		self.output_edit = QLineEdit()
		self.output_edit.setText(self.settings.get("download_path",
		                                           os.path.join(os.path.expanduser('~'), 'Desktop',
		                                                        'BilibiliDownloads')))
		
		browse_btn = QPushButton("浏览")
		browse_btn.setFixedSize(80, 30)
		browse_btn.clicked.connect(self.browse_folder)
		
		output_layout.addWidget(output_label)
		output_layout.addWidget(self.output_edit, 1)
		output_layout.addWidget(browse_btn)
		
		# 按钮区域 - 紧凑布局
		button_widget = QWidget()
		button_layout = QHBoxLayout(button_widget)
		button_layout.setContentsMargins(0, 0, 0, 0)
		button_layout.setSpacing(10)
		
		self.download_btn = QPushButton("下载")
		self.download_btn.setFixedSize(100, 40)
		self.download_btn.setObjectName("downloadBtn")
		self.download_btn.clicked.connect(self.start_batch_download)
		
		clear_btn = QPushButton("清空")
		clear_btn.setFixedSize(100, 40)
		clear_btn.setObjectName("clearBtn")
		clear_btn.clicked.connect(self.clear_all_urls)
		
		exit_btn = QPushButton("退出")
		exit_btn.setFixedSize(100, 40)
		exit_btn.setObjectName("exitBtn")
		exit_btn.clicked.connect(self.close_application)
		
		# 添加按钮到布局
		button_layout.addWidget(self.download_btn)
		button_layout.addWidget(clear_btn)
		button_layout.addWidget(exit_btn)
		button_layout.addStretch()
		
		# 功能按钮区域
		func_widget = QWidget()
		func_layout = QHBoxLayout(func_widget)
		func_layout.setContentsMargins(0, 0, 0, 0)
		func_layout.setSpacing(10)
		
		merge_btn = QPushButton("音视频分离?")
		merge_btn.setFixedSize(120, 40)
		merge_btn.clicked.connect(self.open_merge_window)
		
		m4s_btn = QPushButton("已有m4s文件?")
		m4s_btn.setFixedSize(120, 40)
		m4s_btn.clicked.connect(self.open_m4s_window)
		
		func_layout.addWidget(merge_btn)
		func_layout.addWidget(m4s_btn)
		func_layout.addStretch()
		
		# 进度条区域
		progress_widget = QWidget()
		progress_layout = QVBoxLayout(progress_widget)
		progress_layout.setContentsMargins(0, 0, 0, 0)
		
		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setTextVisible(True)
		self.progress_bar.hide()  # 初始隐藏
		
		self.status_label = QLabel("就绪")
		self.status_label.setAlignment(Qt.AlignCenter)
		
		progress_layout.addWidget(self.progress_bar)
		progress_layout.addWidget(self.status_label)
		
		# 日志区域
		log_label = QLabel("下载日志:")
		log_label.setObjectName("logLabel")
		
		self.log_text = QTextEdit()
		self.log_text.setReadOnly(True)
		font = QFont("Consolas", self.settings.get("font_size", 10))
		self.log_text.setFont(font)
		
		# 添加到主布局
		main_layout.addWidget(title_bar)
		main_layout.addWidget(url_container)
		main_layout.addWidget(output_widget)
		main_layout.addWidget(button_widget)
		main_layout.addWidget(func_widget)
		main_layout.addWidget(progress_widget)
		main_layout.addWidget(log_label)
		main_layout.addWidget(self.log_text, 1)
		
		# 应用样式
		self.apply_styles()
		
		# 记录启动
		self.logger.log("SYSTEM", "启动PyQt5版本")
	
	def load_icon(self, path, size):
		"""加载图标"""
		try:
			if os.path.exists(path):
				pixmap = QPixmap(path)
				if not pixmap.isNull():
					pixmap = pixmap.scaled(size[0], size[1],
					                       Qt.KeepAspectRatio,
					                       Qt.SmoothTransformation)
					return QIcon(pixmap)
		except:
			pass
		return None
	
	def apply_theme(self):
		"""应用主题"""
		theme = self.settings.get("theme", "light")
		
		if theme == "dark":
			# 深色主题
			self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                }
                QWidget {
                    color: #ffffff;
                    background-color: #2b2b2b;
                }
                QLabel#titleLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #ffffff;
                    font-family: '微软雅黑';
                }
                QPushButton {
                    font-family: '微软雅黑';
                    font-size: 11px;
                    padding: 8px 16px;
                    border-radius: 4px;
                    border: 1px solid #555;
                }
                QPushButton#backBtn {
                    background-color: #444;
                }
                QPushButton#addBtn {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton#addBtn:hover {
                    background-color: #2980b9;
                }
                QPushButton#downloadBtn {
                    background-color: #27ae60;
                    color: white;
                }
                QPushButton#downloadBtn:hover {
                    background-color: #219653;
                }
                QPushButton#clearBtn {
                    background-color: #f39c12;
                    color: white;
                }
                QPushButton#clearBtn:hover {
                    background-color: #e67e22;
                }
                QPushButton#exitBtn {
                    background-color: #e74c3c;
                    color: white;
                }
                QPushButton#exitBtn:hover {
                    background-color: #c0392b;
                }
                QLineEdit {
                    font-family: '微软雅黑';
                    font-size: 11px;
                    padding: 8px;
                    border: 1px solid #555;
                    border-radius: 4px;
                    background-color: #333;
                    color: #fff;
                }
                QLineEdit:focus {
                    border: 2px solid #80bdff;
                }
                QTextEdit {
                    font-family: 'Consolas';
                    background-color: #333;
                    color: #fff;
                    border: 1px solid #555;
                    border-radius: 4px;
                }
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QLabel#logLabel {
                    font-weight: bold;
                    color: #ffffff;
                }
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #333;
                }
                QProgressBar::chunk {
                    background-color: #3498db;
                    border-radius: 5px;
                }
            """)
		else:
			# 浅色主题
			self.setStyleSheet("""
                QMainWindow {
                    background-color: #f8f9fa;
                }
                QLabel#titleLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #2c3e50;
                    font-family: '微软雅黑';
                }
                QPushButton {
                    font-family: '微软雅黑';
                    font-size: 11px;
                    padding: 8px 16px;
                    border-radius: 4px;
                    border: 1px solid #ced4da;
                }
                QPushButton#backBtn {
                    background-color: #f8f9fa;
                }
                QPushButton#addBtn {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton#addBtn:hover {
                    background-color: #2980b9;
                }
                QPushButton#downloadBtn {
                    background-color: #2ecc71;
                    color: white;
                }
                QPushButton#downloadBtn:hover {
                    background-color: #27ae60;
                }
                QPushButton#clearBtn {
                    background-color: #f39c12;
                    color: white;
                }
                QPushButton#clearBtn:hover {
                    background-color: #e67e22;
                }
                QPushButton#exitBtn {
                    background-color: #e74c3c;
                    color: white;
                }
                QPushButton#exitBtn:hover {
                    background-color: #c0392b;
                }
                QLineEdit {
                    font-family: '微软雅黑';
                    font-size: 11px;
                    padding: 8px;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    background-color: white;
                }
                QLineEdit:focus {
                    border: 2px solid #80bdff;
                }
                QTextEdit {
                    font-family: 'Consolas';
                    background-color: white;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                }
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QLabel#logLabel {
                    font-weight: bold;
                    color: #2c3e50;
                }
                QProgressBar {
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    text-align: center;
                    background-color: white;
                }
                QProgressBar::chunk {
                    background-color: #3498db;
                    border-radius: 5px;
                }
            """)
	
	def apply_styles(self):
		"""应用样式"""
		font_size = self.settings.get("font_size", 11)
		
		# 更新字体大小
		font = QFont("微软雅黑", font_size)
		self.setFont(font)
	
	def add_url_widget(self, initial=False):
		"""添加URL输入框"""
		url_widget = QWidget()
		url_layout = QHBoxLayout(url_widget)
		url_layout.setContentsMargins(0, 0, 0, 0)
		url_layout.setSpacing(10)
		
		label = QLabel(f"链接(BV号):")
		label.setFixedWidth(80)
		
		url_edit = QLineEdit()
		
		if not initial:
			# 删除按钮
			delete_icon = self.load_icon(DELETE_ICON_PATH, (20, 20))
			delete_btn = QPushButton()
			if delete_icon:
				delete_btn.setIcon(delete_icon)
			else:
				delete_btn.setText("×")
			delete_btn.setFixedSize(30, 30)
			delete_btn.clicked.connect(lambda: self.remove_url_widget(url_widget, url_edit))
			url_layout.addWidget(delete_btn)
		
		url_layout.addWidget(label)
		url_layout.addWidget(url_edit, 1)
		
		self.url_scroll_layout.addWidget(url_widget)
		self.url_widgets.append({'widget': url_widget, 'edit': url_edit})
	
	def remove_url_widget(self, widget, edit):
		"""移除URL输入框"""
		for i, item in enumerate(self.url_widgets):
			if item['edit'] == edit:
				self.url_widgets.pop(i)
				break
		widget.deleteLater()
	
	def browse_folder(self):
		"""浏览文件夹"""
		current_path = self.output_edit.text()
		folder = QFileDialog.getExistingDirectory(
			self, "选择输出目录", current_path
		)
		if folder:
			self.output_edit.setText(folder)
	
	def clear_all_urls(self):
		"""清空所有URL"""
		if self.url_widgets:
			reply = QMessageBox.question(
				self, '确认', '确定要清空所有视频链接吗？',
				QMessageBox.Yes | QMessageBox.No, QMessageBox.No
			)
			
			if reply == QMessageBox.Yes:
				# 保留第一个，删除其他
				for item in self.url_widgets[1:]:
					item['widget'].deleteLater()
				self.url_widgets = self.url_widgets[:1]
				self.url_widgets[0]['edit'].clear()
	
	def start_batch_download(self):
		"""开始批量下载"""
		if self.is_downloading:
			QMessageBox.warning(self, "提示", "当前正在下载中，请等待完成！")
			return
		
		# 获取所有URL
		urls = []
		for item in self.url_widgets:
			url = item['edit'].text().strip()
			if url:
				urls.append(url)
		
		if not urls:
			QMessageBox.warning(self, "提示", "请至少输入一个视频链接！")
			return
		
		output_path = self.output_edit.text().strip()
		if not output_path:
			QMessageBox.warning(self, "提示", "请选择输出目录！")
			return
		
		# 创建输出目录
		try:
			os.makedirs(output_path, exist_ok=True)
		except Exception as e:
			QMessageBox.critical(self, "错误", f"无法创建输出目录: {str(e)}")
			return
		
		# 显示进度条
		self.progress_bar.show()
		self.progress_bar.setValue(0)
		self.status_label.setText("开始下载...")
		
		# 禁用下载按钮
		self.download_btn.setEnabled(False)
		self.is_downloading = True
		
		# 清空日志
		self.log_text.clear()
		self.log_text.append(f"开始批量下载，共{len(urls)}个视频")
		
		# 启动下载线程
		self.download_workers = []
		self.total_downloads = len(urls)
		self.completed_downloads = 0
		
		for url in urls:
			worker = DownloadWorker(url, output_path, self.settings)
			worker.progress_signal.connect(self.update_progress)
			worker.log_signal.connect(self.update_log)
			worker.finished_signal.connect(self.on_download_finished)
			worker.start()
			self.download_workers.append(worker)
	
	def update_progress(self, progress, message):
		"""更新进度"""
		self.progress_bar.setValue(progress)
		self.status_label.setText(message)
	
	def update_log(self, message):
		"""更新日志"""
		self.log_text.append(message)
		# 滚动到底部
		cursor = self.log_text.textCursor()
		cursor.movePosition(QTextCursor.End)
		self.log_text.setTextCursor(cursor)
	
	def on_download_finished(self, success, message):
		"""单个下载完成"""
		self.completed_downloads += 1
		
		if success:
			self.log_text.append(f"✅ {message}")
		else:
			self.log_text.append(f"❌ {message}")
		
		# 计算总体进度
		overall_progress = int((self.completed_downloads / self.total_downloads) * 100)
		self.progress_bar.setValue(overall_progress)
		
		# 检查是否所有下载都完成
		if self.completed_downloads >= self.total_downloads:
			self.is_downloading = False
			self.download_btn.setEnabled(True)
			self.status_label.setText("下载完成")
			
			# 显示完成消息
			success_count = sum(1 for w in self.download_workers if w.isFinished())
			QMessageBox.information(
				self, "完成",
				f"批量下载完成！\n成功：{success_count}个\n失败：{self.total_downloads - success_count}个"
			)
			
			# 隐藏进度条
			QTimer.singleShot(2000, lambda: self.progress_bar.hide())
	
	@pyqtSlot()
	def open_merge_window(self):
		"""打开音视频合并窗口"""
		if self.merge_window is None or not self.merge_window.isVisible():
			self.merge_window = MergeWindow(self.settings, self)
			self.merge_window.setAttribute(Qt.WA_DeleteOnClose)
			self.merge_window.destroyed.connect(lambda: setattr(self, 'merge_window', None))
		self.merge_window.show()
		self.merge_window.raise_()
		self.merge_window.activateWindow()
	
	@pyqtSlot()
	def open_m4s_window(self):
		"""打开M4S处理窗口"""
		if self.m4s_window is None or not self.m4s_window.isVisible():
			self.m4s_window = M4SProcessorWindow(self.settings, self)
			self.m4s_window.setAttribute(Qt.WA_DeleteOnClose)
			self.m4s_window.destroyed.connect(lambda: setattr(self, 'm4s_window', None))
		self.m4s_window.show()
		self.m4s_window.raise_()
		self.m4s_window.activateWindow()
	
	@pyqtSlot()
	def open_settings_window(self):
		"""打开设置窗口"""
		if self.settings_window is None or not self.settings_window.isVisible():
			self.settings_window = SettingsWindow(self.settings, self)
			self.settings_window.setAttribute(Qt.WA_DeleteOnClose)
			self.settings_window.destroyed.connect(lambda: setattr(self, 'settings_window', None))
			self.settings_window.apply_settings_signal.connect(self.apply_new_settings)
		self.settings_window.show()
		self.settings_window.raise_()
		self.settings_window.activateWindow()
	
	def apply_new_settings(self):
		"""应用新设置"""
		self.apply_theme()
		self.apply_styles()
	
	@pyqtSlot()
	def show_about(self):
		"""显示关于窗口"""
		if self.about_window is None or not self.about_window.isVisible():
			self.about_window = AboutWindow(self)
			self.about_window.setAttribute(Qt.WA_DeleteOnClose)
			self.about_window.destroyed.connect(lambda: setattr(self, 'about_window', None))
		self.about_window.show()
		self.about_window.raise_()
		self.about_window.activateWindow()
	
	@pyqtSlot()
	def show_window(self):
		"""显示主窗口"""
		# 确保窗口正常显示并激活
		if self.isHidden():
			self.showNormal()
		else:
			self.show()
		self.raise_()
		self.activateWindow()
	
	def hide_to_tray(self):
		"""隐藏到托盘"""
		self.hide()
	
	def closeEvent(self, event):
		"""关闭事件 - 改为隐藏到托盘而不是关闭"""
		event.ignore()
		self.hide_to_tray()
	
	def close_application(self):
		"""关闭应用"""
		if self.is_downloading:
			reply = QMessageBox.question(
				self, '确认退出',
				'当前正在下载中，确定要退出吗？',
				QMessageBox.Yes | QMessageBox.No, QMessageBox.No
			)
			if reply == QMessageBox.No:
				return
		
		# 停止所有下载线程
		for worker in self.download_workers:
			worker.stop()
		
		# 停止系统托盘
		self.tray_manager.stop()
		
		self.logger.close()
		QApplication.quit()


# ======================== 关于窗口 ========================
class AboutWindow(QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("关于我们")
		self.setFixedSize(800, 600)
		
		if os.path.exists(ICO_FILE):
			self.setWindowIcon(QIcon(ICO_FILE))
		
		layout = QVBoxLayout(self)
		
		# 使用QWebEngineView显示HTML
		self.web_view = QWebEngineView()
		
		# 加载HTML文件
		self.load_html()
		
		# 关闭按钮
		close_btn = QPushButton("关闭")
		close_btn.clicked.connect(self.accept)
		
		layout.addWidget(self.web_view, 1)
		layout.addWidget(close_btn, 0, Qt.AlignCenter)
	
	def load_html(self):
		"""加载HTML文件"""
		try:
			if os.path.exists(ABOUT_HTML_PATH):
				# 读取HTML文件内容
				with open(ABOUT_HTML_PATH, 'r', encoding='utf-8') as f:
					html_content = f.read()
				
				# 转换为文件URL格式
				html_file_url = QUrl.fromLocalFile(ABOUT_HTML_PATH)
				
				# 设置HTML内容，使用baseUrl确保相对路径正确
				self.web_view.setHtml(html_content, html_file_url)
			else:
				# 如果HTML文件不存在，显示默认内容
				self.show_default_content()
		except Exception as e:
			print(f"加载HTML文件失败: {e}")
			self.show_default_content()
	
	def show_default_content(self):
		"""显示默认内容"""
		default_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: '微软雅黑', Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                    background-color: #f8f9fa;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }
                .logo {
                    text-align: center;
                    margin-bottom: 20px;
                }
                .section {
                    margin: 20px 0;
                }
                .feature-list {
                    list-style-type: none;
                    padding-left: 0;
                }
                .feature-list li {
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }
                .feature-list li:before {
                    content: "✓ ";
                    color: #27ae60;
                    font-weight: bold;
                }
                .warning {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <h1>哔哩哔哩视频批量下载器</h1>
                    <p style="color: #666; font-size: 14px;">版本 2.0.0</p>
                </div>

                <div class="warning">
                    <strong>注意：</strong>未找到 about.html 文件，正在显示默认内容。
                    <br>请将 about.html 文件放置在 ./doc/ 目录下。
                </div>

                <div class="section">
                    <h2>🎯 功能特性</h2>
                    <ul class="feature-list">
                        <li>支持B站视频批量下载</li>
                        <li>智能识别BV/AV号</li>
                        <li>音视频分离与合并</li>
                        <li>M4S文件处理</li>
                        <li>实时下载进度显示</li>
                        <li>系统托盘支持</li>
                        <li>自定义主题设置</li>
                    </ul>
                </div>

                <div class="section">
                    <h2>🛠️ 技术支持</h2>
                    <p>基于 you-get 核心开发</p>
                    <p>使用 PyQt5 构建用户界面</p>
                    <p>支持 Windows 系统</p>
                </div>

                <div class="section">
                    <h2>📄 使用说明</h2>
                    <p>1. 输入B站视频链接或BV号</p>
                    <p>2. 选择输出目录</p>
                    <p>3. 点击下载开始批量处理</p>
                    <p>4. 可在系统托盘中管理程序</p>
                </div>

                <div class="section">
                    <h2>📧 联系我们</h2>
                    <p>如有问题或建议，请通过以下方式联系：</p>
                    <p>Email: support@example.com</p>
                    <p>GitHub: github.com/example</p>
                </div>

                <div class="section" style="text-align: center; color: #666; font-size: 12px;">
                    <p>© 2026 哔哩哔哩下载器 版权所有</p>
                </div>
            </div>
        </body>
        </html>
        """
		self.web_view.setHtml(default_html)


# ======================== 设置窗口 ========================
class SettingsWindow(QDialog):
	apply_settings_signal = pyqtSignal()
	
	def __init__(self, settings, parent=None):
		super().__init__(parent)
		self.settings = settings
		self.init_ui()
	
	def init_ui(self):
		self.setWindowTitle("设置")
		self.setFixedSize(500, 450)
		
		if os.path.exists(ICO_FILE):
			self.setWindowIcon(QIcon(ICO_FILE))
		
		layout = QVBoxLayout(self)
		layout.setContentsMargins(20, 20, 20, 20)
		layout.setSpacing(15)
		
		# 创建选项卡
		tab_widget = QTabWidget()
		
		# 基本设置选项卡
		basic_tab = QWidget()
		basic_layout = QVBoxLayout(basic_tab)
		
		# FFmpeg路径设置
		ffmpeg_group = QGroupBox("FFmpeg设置")
		ffmpeg_layout = QVBoxLayout(ffmpeg_group)
		
		ffmpeg_path_layout = QHBoxLayout()
		ffmpeg_label = QLabel("FFmpeg路径:")
		self.ffmpeg_edit = QLineEdit()
		self.ffmpeg_edit.setText(self.settings.get("ffmpeg_path", ""))
		ffmpeg_browse_btn = QPushButton("浏览")
		ffmpeg_browse_btn.clicked.connect(lambda: self.browse_file(self.ffmpeg_edit))
		
		ffmpeg_path_layout.addWidget(ffmpeg_label)
		ffmpeg_path_layout.addWidget(self.ffmpeg_edit, 1)
		ffmpeg_path_layout.addWidget(ffmpeg_browse_btn)
		
		ffmpeg_layout.addLayout(ffmpeg_path_layout)
		basic_layout.addWidget(ffmpeg_group)
		
		# 下载器路径设置
		downloader_group = QGroupBox("下载器设置")
		downloader_layout = QVBoxLayout(downloader_group)
		
		downloader_path_layout = QHBoxLayout()
		downloader_label = QLabel("下载器路径:")
		self.downloader_edit = QLineEdit()
		self.downloader_edit.setText(self.settings.get("downloader_path", ""))
		downloader_browse_btn = QPushButton("浏览")
		downloader_browse_btn.clicked.connect(lambda: self.browse_file(self.downloader_edit))
		
		downloader_path_layout.addWidget(downloader_label)
		downloader_path_layout.addWidget(self.downloader_edit, 1)
		downloader_path_layout.addWidget(downloader_browse_btn)
		
		downloader_layout.addLayout(downloader_path_layout)
		basic_layout.addWidget(downloader_group)
		
		# 下载设置
		download_settings_group = QGroupBox("下载设置")
		download_settings_layout = QGridLayout(download_settings_group)
		
		# 下载路径
		download_path_label = QLabel("默认下载路径:")
		self.download_path_edit = QLineEdit()
		self.download_path_edit.setText(self.settings.get("download_path", ""))
		download_path_browse_btn = QPushButton("浏览")
		download_path_browse_btn.clicked.connect(lambda: self.browse_folder(self.download_path_edit))
		
		# 最大同时下载数
		max_downloads_label = QLabel("最大同时下载:")
		self.max_downloads_spin = QSpinBox()
		self.max_downloads_spin.setRange(1, 10)
		self.max_downloads_spin.setValue(self.settings.get("max_downloads", 3))
		
		download_settings_layout.addWidget(download_path_label, 0, 0)
		download_settings_layout.addWidget(self.download_path_edit, 0, 1)
		download_settings_layout.addWidget(download_path_browse_btn, 0, 2)
		download_settings_layout.addWidget(max_downloads_label, 1, 0)
		download_settings_layout.addWidget(self.max_downloads_spin, 1, 1)
		
		basic_layout.addWidget(download_settings_group)
		basic_layout.addStretch()
		
		# 外观设置选项卡
		appearance_tab = QWidget()
		appearance_layout = QVBoxLayout(appearance_tab)
		
		# 字体大小
		font_group = QGroupBox("字体设置")
		font_layout = QHBoxLayout(font_group)
		
		font_label = QLabel("字体大小:")
		self.font_spin = QSpinBox()
		self.font_spin.setRange(8, 20)
		self.font_spin.setValue(self.settings.get("font_size", 11))
		
		font_layout.addWidget(font_label)
		font_layout.addWidget(self.font_spin)
		font_layout.addStretch()
		appearance_layout.addWidget(font_group)
		
		# 主题选择
		theme_group = QGroupBox("主题设置")
		theme_layout = QVBoxLayout(theme_group)
		
		self.theme_combo = QComboBox()
		self.theme_combo.addItems(["浅色主题", "深色主题"])
		current_theme = self.settings.get("theme", "light")
		self.theme_combo.setCurrentText("深色主题" if current_theme == "dark" else "浅色主题")
		
		theme_layout.addWidget(self.theme_combo)
		appearance_layout.addWidget(theme_group)
		
		# 开机自启
		auto_start_group = QGroupBox("启动设置")
		auto_start_layout = QVBoxLayout(auto_start_group)
		
		self.auto_start_check = QCheckBox("开机自动启动")
		self.auto_start_check.setChecked(self.settings.get("auto_start", False))
		
		auto_start_layout.addWidget(self.auto_start_check)
		appearance_layout.addWidget(auto_start_group)
		
		appearance_layout.addStretch()
		
		# 添加选项卡
		tab_widget.addTab(basic_tab, "基本设置")
		tab_widget.addTab(appearance_tab, "外观设置")
		
		# 按钮区域
		button_layout = QHBoxLayout()
		
		save_btn = QPushButton("保存设置")
		save_btn.clicked.connect(self.save_settings)
		cancel_btn = QPushButton("取消")
		cancel_btn.clicked.connect(self.reject)
		
		button_layout.addStretch()
		button_layout.addWidget(save_btn)
		button_layout.addWidget(cancel_btn)
		
		# 添加到主布局
		layout.addWidget(tab_widget)
		layout.addLayout(button_layout)
	
	def browse_file(self, line_edit):
		"""浏览文件"""
		file_path, _ = QFileDialog.getOpenFileName(
			self, "选择文件", "", "可执行文件 (*.exe);;所有文件 (*.*)"
		)
		if file_path:
			line_edit.setText(file_path)
	
	def browse_folder(self, line_edit):
		"""浏览文件夹"""
		folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
		if folder:
			line_edit.setText(folder)
	
	def save_settings(self):
		"""保存设置"""
		try:
			# 保存FFmpeg路径
			ffmpeg_path = self.ffmpeg_edit.text().strip()
			if ffmpeg_path:
				self.settings.set("ffmpeg_path", ffmpeg_path)
			
			# 保存下载器路径
			downloader_path = self.downloader_edit.text().strip()
			if downloader_path:
				self.settings.set("downloader_path", downloader_path)
			
			# 保存字体大小
			self.settings.set("font_size", self.font_spin.value())
			
			# 保存主题
			theme_text = self.theme_combo.currentText()
			self.settings.set("theme", "dark" if theme_text == "深色主题" else "light")
			
			# 保存下载路径
			download_path = self.download_path_edit.text().strip()
			if download_path:
				self.settings.set("download_path", download_path)
			
			# 保存其他设置
			self.settings.set("max_downloads", self.max_downloads_spin.value())
			self.settings.set("auto_start", self.auto_start_check.isChecked())
			
			QMessageBox.information(self, "成功", "设置已保存！")
			self.apply_settings_signal.emit()
			self.accept()
		
		except Exception as e:
			QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")


# ======================== 音视频合并窗口 ========================
class MergeWindow(QDialog):
	def __init__(self, settings, parent=None):
		super().__init__(parent)
		self.settings = settings
		self.video_file = ""
		self.audio_file = ""
		self.init_ui()
	
	def init_ui(self):
		self.setWindowTitle("音视频合并工具")
		self.setFixedSize(600, 300)
		
		if os.path.exists(ICO_FILE):
			self.setWindowIcon(QIcon(ICO_FILE))
		
		layout = QVBoxLayout(self)
		layout.setContentsMargins(20, 20, 20, 20)
		layout.setSpacing(15)
		
		# 文件选择区域
		file_group = QGroupBox("文件选择")
		file_layout = QGridLayout(file_group)
		
		# 视频文件
		video_label = QLabel(f"视频文件(*[00].mp4):")
		self.video_edit = QLineEdit()
		self.video_edit.setReadOnly(True)
		video_btn = QPushButton("选择")
		video_btn.clicked.connect(self.select_video_file)
		
		# 音频文件
		audio_label = QLabel(f"音频文件(*[01].mp4):")
		self.audio_edit = QLineEdit()
		self.audio_edit.setReadOnly(True)
		audio_btn = QPushButton("选择")
		audio_btn.clicked.connect(self.select_audio_file)
		
		file_layout.addWidget(video_label, 0, 0)
		file_layout.addWidget(self.video_edit, 0, 1)
		file_layout.addWidget(video_btn, 0, 2)
		file_layout.addWidget(audio_label, 1, 0)
		file_layout.addWidget(self.audio_edit, 1, 1)
		file_layout.addWidget(audio_btn, 1, 2)
		
		# 进度区域
		progress_group = QGroupBox("合并进度")
		progress_layout = QVBoxLayout(progress_group)
		
		progress_h_layout = QHBoxLayout()
		progress_label = QLabel("合并进度：")
		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		
		progress_h_layout.addWidget(progress_label)
		progress_h_layout.addWidget(self.progress_bar, 1)
		
		self.status_label = QLabel("就绪")
		self.status_label.setAlignment(Qt.AlignCenter)
		
		progress_layout.addLayout(progress_h_layout)
		progress_layout.addWidget(self.status_label)
		
		# 合并按钮
		self.merge_btn = QPushButton("开始合并")
		self.merge_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
		
		# 添加到主布局
		layout.addWidget(file_group)
		layout.addWidget(progress_group)
		layout.addWidget(self.merge_btn, 0, Qt.AlignCenter)
		layout.addStretch()
	
	def select_video_file(self):
		"""选择视频文件"""
		file_path, _ = QFileDialog.getOpenFileName(
			self, "选择视频文件", "",
			"MP4文件 (*.mp4);;所有文件 (*.*)"
		)
		if file_path and "[00].mp4" in file_path:
			self.video_file = file_path
			self.video_edit.setText(file_path)
		elif file_path:
			QMessageBox.warning(self, "警告", "请选择后缀为[00].mp4的视频文件！")
	
	def select_audio_file(self):
		"""选择音频文件"""
		file_path, _ = QFileDialog.getOpenFileName(
			self, "选择音频文件", "",
			"MP4文件 (*.mp4);;所有文件 (*.*)"
		)
		if file_path and "[01].mp4" in file_path:
			self.audio_file = file_path
			self.audio_edit.setText(file_path)
		elif file_path:
			QMessageBox.warning(self, "警告", "请选择后缀为[01].mp4的音频文件！")


# ======================== M4S处理窗口 ========================
class M4SProcessorWindow(QDialog):
	def __init__(self, settings, parent=None):
		super().__init__(parent)
		self.settings = settings
		self.selected_dir = None
		self.init_ui()
	
	def init_ui(self):
		self.setWindowTitle("M4S文件处理工具")
		self.setFixedSize(500, 400)
		
		if os.path.exists(ICO_FILE):
			self.setWindowIcon(QIcon(ICO_FILE))
		
		layout = QVBoxLayout(self)
		layout.setContentsMargins(20, 20, 20, 20)
		layout.setSpacing(15)
		
		# 标题
		title_label = QLabel("M4S文件处理工具")
		title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
		title_label.setAlignment(Qt.AlignCenter)
		
		# 说明
		desc_label = QLabel(
			"此功能用于处理已有的M4S文件\n"
			"请选择包含M4S文件的目录进行合并处理"
		)
		desc_label.setAlignment(Qt.AlignCenter)
		desc_label.setWordWrap(True)
		
		# 文件选择
		file_group = QGroupBox("文件选择")
		file_layout = QVBoxLayout(file_group)
		
		select_btn = QPushButton("选择M4S文件目录")
		select_btn.clicked.connect(self.select_directory)
		
		self.path_label = QLabel("未选择目录")
		self.path_label.setWordWrap(True)
		
		file_layout.addWidget(select_btn)
		file_layout.addWidget(self.path_label)
		
		# 处理按钮
		self.process_btn = QPushButton("开始处理")
		self.process_btn.setEnabled(False)
		self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
		
		# 进度条
		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.hide()
		
		# 状态标签
		self.status_label = QLabel("就绪")
		self.status_label.setAlignment(Qt.AlignCenter)
		
		# 添加到布局
		layout.addWidget(title_label)
		layout.addWidget(desc_label)
		layout.addWidget(file_group)
		layout.addWidget(self.process_btn, 0, Qt.AlignCenter)
		layout.addWidget(self.progress_bar)
		layout.addWidget(self.status_label)
		layout.addStretch()
	
	def select_directory(self):
		"""选择目录"""
		directory = QFileDialog.getExistingDirectory(self, "选择M4S文件目录")
		if directory:
			self.selected_dir = directory
			self.path_label.setText(f"已选择: {directory}")
			self.process_btn.setEnabled(True)
			
			# 检查目录中是否有M4S文件
			m4s_files = [f for f in os.listdir(directory) if f.endswith('.m4s')]
			if m4s_files:
				self.status_label.setText(f"找到 {len(m4s_files)} 个M4S文件")
			else:
				self.status_label.setText("未找到M4S文件")
				self.process_btn.setEnabled(False)


# ======================== 应用程序类 ========================
class BilibiliDownloaderApp(QApplication):
	def __init__(self, argv):
		super().__init__(argv)
		self.setApplicationName("哔哩哔哩下载器")
		self.setApplicationVersion("2.0.0")
		
		# 关键修复：阻止应用在最后一个窗口关闭时退出
		self.setQuitOnLastWindowClosed(False)
		
		# 设置样式
		self.setStyle("Fusion")
		
		# 创建主窗口
		self.main_window = MainWindow()
		self.main_window.show()


def main():
	# 初始化FFmpeg路径
	get_ffmpeg_path()
	
	# 创建并运行应用
	app = BilibiliDownloaderApp(sys.argv)
	sys.exit(app.exec_())


if __name__ == '__main__':
	main()