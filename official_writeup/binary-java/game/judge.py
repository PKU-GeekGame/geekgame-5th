#!/usr/bin/env python3

import os
import subprocess


def run(cmd: str, env: dict[str, str] | None = None) -> None:
  '''
  Runs the given command with a 60-second timeout.
  '''
  try:
    result = subprocess.run(cmd, shell=True, timeout=60, env=env)
    if result.returncode != 0:
      print(f'命令 `{cmd.split()[0]}` 执行失败！')
      exit(result.returncode)
  except subprocess.TimeoutExpired:
    print(f'命令 `{cmd.split()[0]}` 执行超过 60 秒！')
    exit(-1)


if __name__ == '__main__':
  os.chdir('/root')

  # Get flag id.
  print('欢迎来到爪哇！看看哪个 Flag？')
  flag_id = input('请输入 Flag 编号（1, 2 或 3）：').strip()
  if flag_id not in ('1', '2', '3'):
    print('无效的 Flag 编号！')
    exit(1)

  # Read Java code from stdin.
  print('请输入你的 Java 代码（以单独一行 END 结束，不超过 32 KB）：')
  java_code = ''
  while True:
    line = input()
    if line.strip() == 'END':
      break
    java_code += line + '\n'
    if len(java_code.encode()) > 32 * 1024:
      print('代码过长！')
      exit(1)

  # Compile Java code.
  print('正在编译...')
  with open('Solution.java', 'w') as f:
    f.write(java_code)
  run('javac Solution.java')

  # Setup class files.
  run(f'cp -rf /game/flag{flag_id}/* .')

  # Setup flag.
  try:
    with open(f'/flag{flag_id}', 'r') as f:
      flag = f.read().strip()
  except FileNotFoundError:
    flag = 'notflag{just_for_debug}'
  env = os.environ.copy()
  env[f'FLAG{flag_id}'] = flag

  # Run Java code.
  print('正在运行...')
  run('java -Djava.library.path=. --enable-native-access=ALL-UNNAMED '
      f'-javaagent:blocker.jar Flag{flag_id} Solution.class',
      env=env)
