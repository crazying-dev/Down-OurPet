import pathlib

import configparser
import time
import os

config_file = 'config.ini'
encoding='utf-8'
config = configparser.ConfigParser()
config.read(config_file, encoding=encoding)

def log_write(log_head , log_message, log_ip, log_id=int(time.time() * 10000000000000), log_time=time.strftime('%Y.%m.%d %H:%M:%S')):
	try:
		with open(os.path.join(config.get('path', 'logs'), time.strftime('%Y-%m-%d')), 'a', encoding=config.get('info', 'encoding')) as f:
			f.write('[{}]\n\ttime:{}\n\t\tid:{}\n\t\t\tip:{}\n\t\t\t\t{}\n\n'.format(log_head, log_time, log_id, log_ip, log_message))
	except:
		mkdir('logs')
		with open(os.path.join('logs', time.strftime('%Y-%m-%d')), 'a', encoding=encoding) as f:
			f.write('[{}]\n\ttime:{}\n\t\tid:{}\n\t\t\tip:{}\n\t\t\t\t{}\n\n'.format(log_head, log_time, log_id, log_ip,log_message))


def mkdir(path):
		path = pathlib.Path(path)
		# 1. 若路径已存在：是文件夹则返回 True，是文件则返回 False
		if path.exists():
			if path.is_dir(): # 文件夹→True，文件→False
				return True
		# 2. 路径不存在：尝试创建文件夹
		try:
			path.mkdir(parents=True)
			return True
		except Exception as e:
			return False