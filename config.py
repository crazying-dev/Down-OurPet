import time
import json
import configparser
import os
import pathlib
import log

config_file = 'config.ini'
version = '1.0.0'
this_path = os.path.dirname(os.path.abspath(__file__))
encoding='utf-8'
cookies = {}
error = 0

class config_is_error(Exception):
	pass

class config_do:
	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read(config_file, encoding=encoding)
	
	def write_ini_file(self):
		# 获取当前程序所在目录
		current_dir = os.path.dirname(os.path.abspath(__file__))
		print(f"程序所在目录: {current_dir}")
		
		
		# [path] 部分 - 使用相对路径
		self.config['path'] = {
			'logs': os.path.join(current_dir, 'logs'),
			'config': os.path.join(current_dir, 'config'),
			'temp': os.path.join(current_dir, 'temp'),
			'DownKyi': os.path.join(current_dir, 'DownKyi'),
			'Cookies': os.path.join(current_dir, 'Cookies'),
			'bats':os.path.join(current_dir, 'bats')
		}
		
		# [app] 部分
		self.config['app'] = {
			'version': '1.0.0',
			'founder': 'OurPet工作室'
		}
		
		# [info] 部分
		self.config['info'] = {
			'encoding': 'utf-8'
		}
		
		# 确定INI文件保存路径
		ini_path = config_file
		
		# 写入文件
		with open(ini_path, 'w', encoding='utf-8') as configfile:
			self.config.write(configfile)

		
	
	def mkdir(self, path):
		path = pathlib.Path(path)
		# 1. 若路径已存在：是文件夹则返回 True，是文件则返回 False
		if path.exists():
			if path.is_dir(): # 文件夹→True，文件→False
				log.log_write(log_head='Error -- 0', log_message=f'Directory already exists during creation: {path}', log_ip=1113)
				return True
		# 2. 路径不存在：尝试创建文件夹
		try:
			path.mkdir(parents=True)
			log.log_write(log_head='Success', log_message=f'Directory "{path}" created successfully', log_ip= 1114)
			return True
		except Exception as e:
			log.log_write(log_head='Error -- 10', log_message=f'Unknown error when creating the directory: {e}', log_ip=115)
			return False
		
	def first(self):
		global error
		try:
			config_path = self.config.get("path", "config")
			self.mkdir(config_path)
			with open(os.path.join(config_path, "DownKyi.bin"), "w", encoding=encoding) as f:
				f.write(self.config.get("path", "DownKyi"))
			with open(os.path.join(config_path, "cookies.bin"), "w", encoding=encoding) as f:
				f.write(json.dumps(cookies))
			with open(os.path.join(config_path, 'version'), 'w', encoding=encoding) as f:
				f.write(self.config.get('app', 'version'))
			self.mkdir(os.path.join(config_path, "cookies"))
			

			Cookise_path = self.config.get('path', "cookies")
			self.mkdir(Cookise_path)
			
			log_path = self.config.get('path', "logs")
			self.mkdir(log_path)
			
			temp_path = self.config.get('path', 'temp')
			self.mkdir(temp_path)
			
			bat_path = self.config.get('path', 'bats')
			self.mkdir(bat_path)
			
			log.log_write(log_head='Success', log_message='The first-time loading is success', log_ip=1112)
		except configparser.NoSectionError:
			log.log_write(log_head='Error -- 10', log_message='config_is_error:Can`t find file name is config.ini in object', log_ip=1111)
			log.log_write(log_head='retry', log_message="Retrying due to error config_is_error: Can't find file named config.ini in object. Retry count: 1/1", log_ip=1116)
			self.write_ini_file()
			self.first()
			if error == 1:
				raise config_is_error('Can`t find file name is config.ini in object')
		except Exception as e:
			if error == 0:
				print(e)
				error = 1
				self.first()
			log.log_write(log_head='Error -- 10', log_message=f'Unknown error when initializing config: {e}', log_ip=1119)
			raise e

	def new_cookies(self):
		...

if __name__ == '__main__':
	config_do = config_do()
	config_do.first()