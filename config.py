import shutil
import time
import json
import configparser
import os
import pathlib
import logging

# 配置常量
CONFIG_FILE = 'config.ini'
VERSION = '1.0.0'
ENCODING = 'utf-8'

# 配置日志
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def safe_delete(path):
	"""
	安全删除文件或目录，不抛出异常
	:param path: 文件或目录路径
	:return: True 表示删除成功或文件不存在，False 表示删除失败
	"""
	try:
		if not os.path.exists(path):
			return True
		
		if os.path.isfile(path):
			os.remove(path)
			logger.info(f"成功删除文件: {path}")
		elif os.path.isdir(path):
			shutil.rmtree(path, ignore_errors=True)
			logger.info(f"成功删除目录: {path}")
		
		return True
	except Exception as e:
		logger.error(f"删除失败: {path}, 错误: {e}")
		return False


def first():
	"""
	首次初始化函数
	创建必要的目录结构和配置文件
	"""
	logger.info("开始首次初始化...")
	
	# 获取当前程序所在目录
	current_dir = os.path.dirname(os.path.abspath(__file__))
	
	# 创建配置解析器
	config = configparser.ConfigParser()
	
	# 检查配置文件是否存在
	config_file_path = CONFIG_FILE
	
	# 如果配置文件不存在，创建默认配置
	if not os.path.exists(config_file_path):
		logger.info("配置文件不存在，创建默认配置...")
		
		# [path] 部分 - 使用相对路径
		config['path'] = {
			'logs': os.path.join(current_dir, 'logs'),
			'config': os.path.join(current_dir, 'config'),
			'temp': os.path.join(current_dir, 'temp'),
			'DownKyi': os.path.join(current_dir, 'DownKyi'),
			'Cookies': os.path.join(current_dir, 'Cookies'),
			'bats': os.path.join(current_dir, 'bats'),
			'ffmpeg':os.path.join(current_dir, 'ffmpeg.exe')
		}
		
		# [app] 部分
		config['app'] = {
			'version': VERSION,
			'founder': 'OurPet工作室'
		}
		
		# [info] 部分
		config['info'] = {
			'encoding': ENCODING
		}
		
		# 写入配置文件
		try:
			with open(config_file_path, 'w', encoding=ENCODING) as configfile:
				config.write(configfile)
				configfile.flush()
			logger.info(f"配置文件创建成功: {config_file_path}")
		except Exception as e:
			logger.error(f"创建配置文件失败: {e}")
			return False
	else:
		logger.info("配置文件已存在，加载配置...")
	
	# 读取配置文件
	try:
		config.read(config_file_path, encoding=ENCODING)
	except Exception as e:
		logger.error(f"读取配置文件失败: {e}")
		# 尝试删除损坏的配置文件并重新创建
		safe_delete(config_file_path)
		return first()  # 递归重试
	
	# 创建必要的目录
	def mkdir(path):
		"""创建目录的辅助函数"""
		try:
			if not os.path.exists(path):
				os.makedirs(path, exist_ok=True)
				logger.info(f"目录创建成功: {path}")
				return True
			else:
				if os.path.isdir(path):
					logger.debug(f"目录已存在: {path}")
					return True
				else:
					logger.error(f"路径存在但不是目录: {path}")
					return False
		except Exception as e:
			logger.error(f"创建目录失败: {path}, 错误: {e}")
			return False
	
	# 获取配置中的路径
	try:
		config_path = config.get("path", "config")
		cookies_path = config.get("path", "Cookies")
		logs_path = config.get("path", "logs")
		temp_path = config.get("path", "temp")
		bats_path = config.get("path", "bats")
		
		# 创建所有必要的目录
		directories = [
			config_path,
			cookies_path,
			logs_path,
			temp_path,
			bats_path
		]
		
		for directory in directories:
			if not mkdir(directory):
				logger.warning(f"目录创建可能失败: {directory}")
		
		# 创建config目录下的子目录和文件
		mkdir(os.path.join(config_path, "cookies"))
		
		# 写入DownKyi.bin
		downkyi_file = os.path.join(config_path, "DownKyi.bin")
		with open(downkyi_file, "w", encoding=ENCODING) as f:
			f.write(config.get("path", "DownKyi"))
		
		# 写入cookies.bin（初始为空字典）
		cookies_file = os.path.join(config_path, "cookies.bin")
		with open(cookies_file, "w", encoding=ENCODING) as f:
			json.dump({}, f, ensure_ascii=False, indent=2)
		
		# 写入version文件
		version_file = os.path.join(config_path, 'version')
		with open(version_file, 'w', encoding=ENCODING) as f:
			f.write(config.get('app', 'version'))
		
		logger.info("首次初始化完成")
		return True
	
	except configparser.NoSectionError as e:
		logger.error(f"配置文件格式错误，缺少必要的节: {e}")
		# 删除损坏的配置文件
		safe_delete(config_file_path)
		# 重新尝试初始化
		return first()
	
	except Exception as e:
		logger.error(f"初始化过程中发生未知错误: {e}")
		return False


# 主入口
if __name__ == '__main__':
	# 执行首次初始化
	success = first()
	if success:
		print("初始化成功完成！")
	else:
		print("初始化失败，请检查日志。")