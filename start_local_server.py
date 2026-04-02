"""启动本地玄学互动服务器"""
import sys, os, subprocess, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

# Kill existing servers
try:
    result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, shell=True)
    for line in result.stdout.split('\n'):
        if ':8000' in line and 'LISTENING' in line:
            pid = line.split()[-1].strip()
            print(f"Killing existing process {pid} on port 8000")
            subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
except:
    pass

time.sleep(1)

# Start new server
print("=" * 50)
print("玄学互动服务器启动中...")
print("本地访问: http://localhost:8000")
print()
print("让手机连接测试：")
print("1. 确保手机和电脑在同一WiFi网络")
print("2. 查看电脑局域网IP（ipconfig）")
print("3. 手机浏览器访问: http://<电脑IP>:8000")
print("4. 如果无法访问，说明Guest网络隔离，请换用手机4G热点")
print()
print("按 Ctrl+C 停止服务器")
print("=" * 50)

from main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
