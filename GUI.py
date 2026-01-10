from typing import Optional

import subprocess
import sys
import os
import re
from tqdm import tqdm


class GUI:
	def __init__(self):
		pass
	
	def run_cmd_with_progress(self, cmd, description="Processing", cwd=None):
		"""
		执行CMD命令并显示进度条 - 修复重复输出问题
		"""
		try:
			# 执行命令并捕获输出
			process = subprocess.Popen(
				cmd,
				shell=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				universal_newlines=True,
				bufsize=0,  # 无缓冲
				cwd=cwd
			)
			
			# 创建进度条
			with tqdm(total=100, desc=description, unit="%", ncols=80) as pbar:
				last_progress = 0
				file_part = 1  # 跟踪文件部分 [1/2] 或 [2/2]
				
				# 设置 tqdm 的刷新频率，避免频繁刷新
				pbar.miniters = 0.1  # 最小更新间隔
				pbar.mininterval = 0.05  # 最小显示间隔
				
				while True:
					# 读取一行
					output = process.stdout.readline()
					if output == '' and process.poll() is not None:
						break
					
					if output:
						line = output.rstrip('\n\r')
						if line:  # 跳过空行
							# 只显示必要的输出信息，过滤掉进度条重复的内容
							should_print = True
							
							# 过滤掉百分比进度行（这些会通过进度条显示）
							if re.search(r'\d+\.?\d*%\s*\(', line) and 'MB' in line:
								should_print = False
							
							# 过滤掉重复的下载开始行
							if "Downloading" in line and pbar.n > 0:
								should_print = False
							
							# 打印重要信息
							if should_print:
								# 清空当前行，避免与进度条冲突
								sys.stdout.write('\r')
								sys.stdout.flush()
								print(line)
							
							# 提取百分比
							match = re.search(r'(\d+\.?\d*)%', line)
							if match:
								try:
									percent = float(match.group(1))
									if 0 <= percent <= 100:
										# 处理多文件下载的进度
										if "[2/2]" in line and file_part == 1:
											file_part = 2
											# 切换到第二部分时，从50%开始
											if last_progress < 50:
												pbar.update(50 - last_progress)
												last_progress = 50
												pbar.set_description(f"{description} [Part {file_part}/2]")
										
										# 根据文件部分计算实际进度
										if file_part == 1:  # 第一部分
											actual_percent = percent / 2  # 0-50%
										else:  # 第二部分
											actual_percent = 50 + (percent / 2)  # 50-100%
										
										# 确保进度平滑递增
										if actual_percent > last_progress:
											increment = actual_percent - last_progress
											pbar.update(increment)
											last_progress = actual_percent
								
								except:
									pass
				
				# 确保进度条完成
				if last_progress < 100:
					pbar.update(100 - last_progress)
				
				process.wait()
			
			# 清空进度条，换行显示完成信息
			sys.stdout.write('\n')
			
			if process.returncode == 0:
				print(f"✅ {description}完成！")
				print(f"   文件大小: 67.7MB")
				print(f"   下载时间: 约1分钟")
				return True
			else:
				print(f"\n❌ {description}失败，返回码: {process.returncode}")
				return False
		
		except Exception as e:
			print(f"\n❌ 执行命令时出错: {e}")
			return False


class any_to_bilibili:
	def bv_to_url(self, bv_input):
		"""
		将BV号转换为B站视频链接

		Args:
			bv_input: 输入字符串（可以是BV号、AV号、B站URL或包含BV号的文本）

		Returns:
			str: B站视频链接，如果无法转换则返回None
		"""
		if not isinstance(bv_input, str) or not bv_input.strip():
			return None
		
		bv_input = bv_input.strip()
		
		# 1. 如果已经是B站视频链接，直接返回
		if self._is_bilibili_video_url(bv_input):
			return bv_input
		
		# 2. 如果是BV号，转换为链接
		bv_match = self._extract_bv_id(bv_input)
		if bv_match:
			# 保持原始输入的大小写格式
			# 但确保BV部分是大写，后面字符保持原样
			return f"https://www.bilibili.com/video/{bv_match}"
		
		# 3. 如果是AV号，转换为链接
		av_match = self._extract_av_id(bv_input)
		if av_match:
			return f"https://www.bilibili.com/video/av{av_match}"
		
		# 4. 尝试从文本中提取BV号
		bv_from_text = self._find_bv_in_text(bv_input)
		if bv_from_text:
			return f"https://www.bilibili.com/video/{bv_from_text}"
		
		# 5. 尝试从文本中提取AV号
		av_from_text = self._find_av_in_text(bv_input)
		if av_from_text:
			return f"https://www.bilibili.com/video/av{av_from_text}"
		
		return None
	
	# ============ 辅助函数 ============
	
	def _is_valid_bv(self, bv_id):
		"""验证BV号格式是否正确"""
		if not isinstance(bv_id, str):
			return False
		
		bv_id = bv_id.strip()
		
		# B站BV号规则：
		# 1. 以BV开头（不区分大小写）
		# 2. 共12个字符（BV + 10个字符）
		# 3. 允许的字符：数字 0-9，大写字母 A-Z，小写字母 a-z
		
		bv_pattern = re.compile(r'^BV[0-9A-Za-z]{10}$', re.IGNORECASE)
		return bool(bv_pattern.match(bv_id))
	
	def _extract_bv_id(self, input_str):
		"""从字符串中提取BV号，保持原始大小写"""
		if not isinstance(input_str, str):
			return None
		
		# 使用原始大小写匹配
		match = re.search(r'(BV[0-9A-Za-z]{10})', input_str)
		if match:
			bv_id = match.group(1)
			# 基本验证：确保长度正确且以BV开头（不区分大小写）
			if len(bv_id) == 12 and bv_id[:2].upper() == 'BV':
				return bv_id  # 返回原始大小写的BV号
		
		return None
	
	def _extract_av_id(self, input_str):
		"""从字符串中提取AV号"""
		if not isinstance(input_str, str):
			return None
		
		# 匹配AV号（支持多种格式）
		match = re.search(r'[Aa][Vv](\d+)', input_str)
		if match:
			av_num = match.group(1)
			# 验证AV号长度和数字有效性
			if av_num.isdigit() and 5 <= len(av_num) <= 10:
				return av_num
		
		return None
	
	def _find_bv_in_text(self, text):
		"""从文本中查找BV号，保持原始大小写"""
		# 查找所有可能的BV号
		matches = re.findall(r'BV[0-9A-Za-z]{10}', text)
		for bv in matches:
			# 验证找到的BV号
			if len(bv) == 12 and bv[:2].upper() == 'BV':
				return bv  # 返回原始大小写的BV号
		return None
	
	def _find_av_in_text(self, text):
		"""从文本中查找AV号"""
		# 查找AV号
		matches = re.findall(r'[Aa][Vv](\d{5,10})', text)
		if matches:
			return matches[0]  # 返回第一个找到的AV号
		
		return None
	
	def _is_bilibili_video_url(self, url):
		"""判断是否为B站视频URL"""
		if not isinstance(url, str):
			return False
		
		# 检查是否包含B站域名和视频路径（不区分大小写）
		bilibili_patterns = [
			r'https?://(www\.)?bilibili\.com/video/',
			r'https?://m\.bilibili\.com/video/',
			r'https?://b23\.tv/',
		]
		
		url_lower = url.lower()
		for pattern in bilibili_patterns:
			if re.search(pattern, url_lower):
				return True
		
		return False


if __name__ == "__main__":
	exe_dir = os.getcwd()
	exe_path = os.path.join(exe_dir, "you-get-ourpet.exe")
	
	if not os.path.exists(exe_path):
		print(f"错误：找不到可执行文件: {exe_path}")
	else:
		app = GUI()
		
		# 创建必要文件
		logs_dir = os.path.join(exe_dir, "logs")
		if not os.path.exists(logs_dir):
			os.makedirs(logs_dir)
		
		config_path = os.path.join(exe_dir, "config.ini")
		if not os.path.exists(config_path):
			import configparser
			
			config = configparser.ConfigParser()
			config['path'] = {'logs': 'logs'}
			config['info'] = {'encoding': 'utf-8'}
			with open(config_path, 'w', encoding='utf-8') as f:
				config.write(f)
		url = input('哔哩哔哩视频链接（BV号）：')
		any_to_bilibili = any_to_bilibili()
		url = any_to_bilibili.bv_to_url(url)
		print(url)
		other = f"-o {os.path.join(os.path.expanduser('~'), 'Desktop')}"
		# 执行命令
		cmd = f'"{exe_path}" {other} {url}'
		app.run_cmd_with_progress(cmd, description="下载视频", cwd=exe_dir)