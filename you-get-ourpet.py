#!/usr/bin/env python3
"""
you-get 封装版（命令行调用模式，兼容所有环境）
文件名: you-get-ourpet.py
用法: you-get-ourpet.exe [URL] [选项]
修复了输出缓冲问题
"""
from typing import Union
import config
import argparse
import configparser
import os
import pathlib
import subprocess
import sys
import time
import traceback
import io


class YouGetWrapper:
	"""you-get 命令行封装（避免模块导入的环境问题）"""
	
	def __init__(self, debug=False, log_file=None):
		self.debug = debug
		self.log_file = log_file or "you-get-ourpet.log"
		
		# 先初始化 config，再调用其他方法
		self.config_file = 'config.ini'
		self.encoding = 'utf-8'
		self.config = configparser.ConfigParser()
		
		# 尝试读取配置文件，如果不存在则创建默认配置
		try:
			self.config.read(self.config_file, encoding=self.encoding)
		except Exception:
			# 如果配置文件不存在，创建默认配置
			self.config['path'] = {'logs': 'logs'}
			self.config['info'] = {'encoding': 'utf-8'}
			with open(self.config_file, 'w', encoding=self.encoding) as f:
				self.config.write(f)
		
		# 找到系统中可用的 you-get 路径
		self.you_get_path = self._find_you_get()
	
	def _log(self, log_head, log_message, log_ip: Union[int, str] = '2xxx', log_id=None, log_time=None):
		"""简化日志方法，避免依赖配置文件"""
		if log_id is None:
			log_id = int(time.time() * 10000000000000)
		if log_time is None:
			log_time = time.strftime('%Y.%m.%d %H:%M:%S')
		
		# 确保日志目录存在
		if not (hasattr(self, 'config') and self.config.has_section('path')):
			config_c = config.config_do()
			config_c.first()
		log_dir = self.config.get('path', 'logs')
		
		os.makedirs(log_dir, exist_ok=True)
		
		# 编码处理
		encoding = 'utf-8'
		if hasattr(self, 'config') and self.config.has_section('info'):
			encoding = self.config.get('info', 'encoding')
		
		log_entry = f'[{log_head}]\n\ttime:{log_time}\n\t\tid:{log_id}\n\t\t\tip:{log_ip}\n\t\t\t\t{log_message}\n\n'
		
		log_filename = os.path.join(log_dir, time.strftime('%Y-%m-%d'))
		try:
			with open(log_filename, 'a', encoding=encoding) as f:
				f.write(log_entry)
		except Exception as e:
			# 如果写入失败，尝试使用默认编码
			try:
				with open(log_filename, 'a', encoding='utf-8') as f:
					f.write(log_entry)
			except:
				# 如果还是失败，打印到控制台
				print(f"无法写入日志文件: {e}")
	
	def mkdir(self, path):
		path = pathlib.Path(path)
		# 1. 若路径已存在：是文件夹则返回 True，是文件则返回 False
		if path.exists():
			if path.is_dir():  # 文件夹→True，文件→False
				return True
		# 2. 路径不存在：尝试创建文件夹
		try:
			path.mkdir(parents=True)
			return True
		except Exception as e:
			return False
	
	def _find_you_get(self):
		"""查找系统中可用的 you-get 可执行文件"""
		try:
			# 优先找 Python Scripts 目录下的 you-get.exe
			scripts_dir = os.path.join(os.path.dirname(sys.executable), "Scripts")
			you_get_exe = os.path.join(scripts_dir, "you-get.exe")
			if os.path.exists(you_get_exe):
				self._log(log_head='Success', log_message=f"找到 you-get: {you_get_exe}", log_ip=2111)
				return you_get_exe
			
			# 找不到则用系统 PATH 中的 you-get
			result = subprocess.run(
				["where", "you-get"],
				capture_output=True,
				text=True,
				encoding="utf-8"
			)
			if result.returncode == 0 and result.stdout.strip():
				you_get_path = result.stdout.strip().split("\n")[0]
				self._log(log_head='Success', log_message=f"找到 you-get: {you_get_path}")
				return you_get_path
			
			self._log(log_head="Error -- 10", log_message="未找到 you-get 可执行文件")
			print("请先安装 you-get：")
			print(r"  C:\Users\Alan_\AppData\Local\Programs\Python\Python39\python.exe -m pip install you-get")
			return None
		except Exception as e:
			self._log(log_message=f"查找 you-get 失败: {str(e)}", log_head="Error -- 10")
			return None
	
	def run_command(self, url: str, **kwargs) -> dict:
		"""执行 you-get 命令行（修复输出缓冲）"""
		if not self.you_get_path:
			error_msg = "未找到 you-get 可执行文件"
			self._log(log_message=f"URL: {url} → {error_msg}", log_head="Error -- 10")
			return {"status": "error", "error": error_msg, "url": url}
		
		# 构建命令行参数
		cmd = [self.you_get_path]
		
		# 输出选项
		if kwargs.get('output_dir'):
			cmd.extend(["-o", str(kwargs['output_dir'])])
		if kwargs.get('format'):
			cmd.extend(["-f", kwargs['format']])
		
		# 功能选项
		if kwargs.get('info_only'):
			cmd.append("-i")
		if kwargs.get('json_output'):
			cmd.append("--json")
		if kwargs.get('caption'):
			cmd.append("-c")
		if kwargs.get('no_merge'):
			cmd.append("--no-merge")
		if kwargs.get('no_proxy'):
			cmd.append("--no-proxy")
		if kwargs.get('cookies'):
			cmd.extend(["--cookies", kwargs['cookies']])
		if kwargs.get('timeout'):
			cmd.extend(["-t", str(kwargs['timeout'])])
		if self.debug:
			cmd.append("--debug")
		
		# 添加视频 URL
		cmd.append(url)
		
		self._log(log_head='Run', log_message=f"执行命令: {' '.join(cmd)}")
		
		try:
			# 修复：使用 Popen 实时获取输出，而不是 run
			process = subprocess.Popen(
				cmd,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				universal_newlines=True,
				bufsize=1,  # 行缓冲
				encoding="utf-8",
				errors="ignore"
			)
			
			output_lines = []
			
			# 实时读取输出
			while True:
				line = process.stdout.readline()
				if line == '' and process.poll() is not None:
					break
				if line:
					# 立即打印输出（无缓冲）
					print(line, end='', flush=True)
					output_lines.append(line)
			
			process.wait()
			output = ''.join(output_lines)
			
			if process.returncode == 0:
				self._log(log_head='Success', log_message=f"URL: {url} → 操作成功")
				return {
					"status": "success",
					"stdout": output,
					"stderr": "",
					"url": url,
					"returncode": 0
				}
			else:
				error_msg = f"you-get 执行失败（退出码：{process.returncode}）"
				self._log(log_message=f"URL: {url} → {error_msg}", log_head="Error -- 10")
				return {
					"status": "error",
					"error": error_msg,
					"stdout": output,
					"stderr": "",
					"url": url,
					"returncode": process.returncode
				}
		except Exception as e:
			error_msg = str(e)
			tb = traceback.format_exc()
			self._log(log_message=f"URL: {url} → 错误: {error_msg}\n堆栈: {tb}", log_head="Error -- 10")
			return {
				"status": "error",
				"error": error_msg,
				"traceback": tb,
				"url": url,
				"returncode": 1
			}
	
	def download(self, url: str, output_dir: str = ".", **kwargs) -> dict:
		"""下载视频"""
		return self.run_command(url, output_dir=output_dir, **kwargs)
	
	def get_info(self, url: str) -> dict:
		"""仅获取视频信息"""
		return self.run_command(url, info_only=True)
	
	def batch_download(self, urls: list, output_dir: str = ".", **kwargs) -> list:
		"""批量下载"""
		results = []
		for i, url in enumerate(urls, 1):
			print(f"\n[{i}/{len(urls)}] 处理 URL: {url}")
			result = self.download(url, output_dir, **kwargs)
			results.append({"url": url, "result": result})
		return results


# ================ 命令行接口 ================
def get_parser():
	"""创建并返回参数解析器（解决作用域问题）"""
	parser = argparse.ArgumentParser(
		description="you-get 封装版（命令行调用模式）",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
示例用法:
  1. 下载单个视频：
     %(prog)s https://www.bilibili.com/video/BV1xx411c7mD
  2. 指定下载目录：
     %(prog)s -o "D:\\B站下载" https://www.bilibili.com/video/BV1xx411c7mD
  3. 仅查看视频信息：
     %(prog)s -i https://www.bilibili.com/video/BV1xx411c7mD
  4. 批量下载（从文件读取URL）：
     %(prog)s -b urls.txt -o "./批量下载"
  5. 带调试模式运行：
     %(prog)s --debug https://www.bilibili.com/video/BV1xx411c7mD
        """
	)
	
	# 核心参数
	parser.add_argument('url', nargs='?', help='单个视频URL')
	
	# 选项
	parser.add_argument('-o', '--output-dir', default='.', help='保存目录（默认：当前目录）')
	parser.add_argument('-f', '--format', help='指定视频格式（如 dash-flv480-AV1）')
	parser.add_argument('-i', '--info-only', action='store_true', help='仅查看信息，不下载')
	parser.add_argument('-c', '--caption', action='store_true', help='下载字幕')
	parser.add_argument('--no-merge', action='store_true', help='不合并视频片段')
	parser.add_argument('--no-proxy', action='store_true', help='不使用代理')
	parser.add_argument('--cookies', help='指定cookies文件路径')
	parser.add_argument('-t', '--timeout', type=int, default=600, help='超时时间（默认600秒）')
	parser.add_argument('-b', '--batch-file', help='批量下载文件（每行一个URL）')
	parser.add_argument('--urls', nargs='+', help='批量URL（空格分隔）')
	parser.add_argument('--debug', action='store_true', help='调试模式')
	parser.add_argument('--log-file', help='日志文件路径（默认：you-get-ourpet.log）')
	
	return parser


def parse_args():
	"""解析命令行参数"""
	parser = get_parser()
	return parser.parse_args()


def read_urls_from_file(filepath: str) -> list:
	"""读取批量URL文件"""
	urls = []
	try:
		with open(filepath, 'r', encoding='utf-8') as f:
			for line in f:
				line = line.strip()
				if line and not line.startswith('#'):
					urls.append(line)
		print(f"从文件 {filepath} 读取到 {len(urls)} 个URL")
	except Exception as e:
		print(f"读取文件失败: {str(e)}")
	return urls


def print_result(result: dict):
	"""打印执行结果"""
	if result['status'] == 'success':
		print(f"\nURL: {result['url']} 操作成功")
		if result['stdout']:
			print("输出：")
			print(result['stdout'])
	else:
		print(f"\nURL: {result['url']} 操作失败")
		print(f"错误：{result['error']}")
		if result.get('stderr'):
			print("错误详情：")
			print(result['stderr'])
		if result.get('traceback') and '--debug' in sys.argv:
			print("\n堆栈信息：")
			print(result['traceback'])


def main():
	"""主函数"""
	# 先创建解析器（避免无参数时找不到 parser）
	parser = get_parser()
	args = parse_args()
	
	# 初始化封装器
	wrapper = YouGetWrapper(
		debug=args.debug,
		log_file=args.log_file
	)
	
	if not wrapper.you_get_path:
		sys.exit(1)
	
	# 批量下载（文件）
	if args.batch_file:
		urls = read_urls_from_file(args.batch_file)
		if not urls:
			sys.exit(1)
		results = wrapper.batch_download(
			urls,
			output_dir=args.output_dir,
			format=args.format,
			caption=args.caption,
			no_merge=args.no_merge,
			no_proxy=args.no_proxy,
			cookies=args.cookies,
			timeout=args.timeout
		)
		# 统计结果
		success = sum(1 for item in results if item['result']['status'] == 'success')
		fail = len(results) - success
		print(f"\n{'=' * 50}")
		print(f"成功 {success} / 失败 {fail}")
		print(f"{'=' * 50}")
	# 批量下载（命令行URL）
	elif args.urls:
		results = wrapper.batch_download(
			args.urls,
			output_dir=args.output_dir,
			format=args.format,
			caption=args.caption,
			no_merge=args.no_merge,
			no_proxy=args.no_proxy,
			cookies=args.cookies,
			timeout=args.timeout
		)
		success = sum(1 for item in results if item['result']['status'] == 'success')
		fail = len(results) - success
		print(f"\n{'=' * 50}")
		print(f"成功 {success} / 失败 {fail}")
		print(f"{'=' * 50}")
	# 单个URL操作
	elif args.url:
		if args.info_only:
			result = wrapper.get_info(args.url)
		else:
			result = wrapper.download(
				args.url,
				output_dir=args.output_dir,
				format=args.format,
				caption=args.caption,
				no_merge=args.no_merge,
				no_proxy=args.no_proxy,
				cookies=args.cookies,
				timeout=args.timeout
			)
		print_result(result)
		sys.exit(result['returncode'])
	# 无参数：打印帮助信息
	else:
		# 直接调用 parser.print_help()（此时 parser 已创建）
		parser.print_help()
		sys.exit(1)


if __name__ == "__main__":
	# 设置无缓冲输出
	if sys.platform == "win32":
		import msvcrt
		import ctypes
		
		# Windows: 设置控制台模式
		kernel32 = ctypes.windll.kernel32
		kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
	
	# 强制无缓冲
	sys.stdout = io.TextIOWrapper(open(sys.stdout.fileno(), 'wb', 0), write_through=True)
	sys.stderr = io.TextIOWrapper(open(sys.stderr.fileno(), 'wb', 0), write_through=True)
	
	main()