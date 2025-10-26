编译ELF

```
gcc -O2 -fPIC -fno-asynchronous-unwind-tables -fno-unwind-tables -ffunction-sections -fdata-sections -Wl,--gc-sections -s challenge_min_obf.c -o challenge_min_obf
```

进行patch生成challenge_min_obf_patched

```
python3 patch.py
```

