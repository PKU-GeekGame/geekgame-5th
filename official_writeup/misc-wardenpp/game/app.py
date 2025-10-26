import sys
import re
import os
import subprocess
import tempfile


print("""
🎮 C++ in your area! 🎮
    Test your code's worthiness! Can you still steal the flag if you have only the compilation result?

Rules:
1. Submit your C++ code, please end it with an extra line containing only 'END', e.g.
    ```
    int main() {
       return 0; 
    }
    END
    ```
2. Our compiler will judge its syntax
3. Verdict: Success or Defeat!

No execution, just pure compilation checking.
Good luck, brave hacker!
P.S Flag is at /flag on the server :)
""")
sys.stdout.flush()

def compile_check(code):
    with tempfile.NamedTemporaryFile(suffix='.cpp', delete=False) as tmp:
        tmp.write(code.encode())
        tmp.flush()
        
        result = subprocess.run(['g++-15', tmp.name], 
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              text=True)
        
        os.unlink(tmp.name)
        
        if result.returncode == 0:
            print("✅ Compilation Success! Your code is syntactically perfect!")
        else:
            print("❌ Compilation Failed! ")
            print(result.stderr)
        sys.stdout.flush()

for i in range(400):

    code = ""
    
    while True:
        line = sys.stdin.readline()
        if line.strip() == "END":
            break
        code += line
    
    if len(code) > 0x1000:
        print("❌ Code too long! Limit is 4096 characters.")
        sys.stdout.flush()
        continue
    compile_check(code)

