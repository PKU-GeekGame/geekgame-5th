# [Algorithm] 滑滑梯加密

- 命题人：jiegec
- 拿到 easy flag 只能给你 3.3：150 分
- 拿到 hard flag 才有 4.0：400 分

## 题目描述

<p>小帅最近迷上了密码学，正埋头研究 DES 对称加密算法。课堂上，老师推了推眼镜，严肃地告诫他：“DES 早已过时，如今必须使用更强大的 AES。”</p>
<p>但小帅不以为意，叛逆的火花在眼中闪烁。一个大胆的念头在他脑海中炸开：“如果<strong>把 DES 的 F 函数替换成坚不可摧的 SHA1 散列算法</strong>呢？既然核心已经强化，其他部分做些妥协也无妨吧？”</p>
<p>这个想法让他兴奋不已。说干就干，他设计出了一套全新的加密算法。出于对滑滑梯的执念，他给这个算法起了个俏皮的名字——<strong>滑滑梯加密算法</strong>。</p>
<p>当这份作业摆在讲台上时，密码学老师拿起纸张，嘴角勾起一抹意味深长的弧度。“有意思，”他轻笑着，声音里带着几分玩味，“这个算法，我十分钟就能破解。”他的目光扫过全班，抛出致命诱惑：“谁能破解它，我这门课直接给 4.0！”</p>
<p>教室里一片寂静，只有心跳声在回荡。坐在角落的你抬起头，目光与老师相遇。</p>
<p>一个改变成绩的机会就在眼前——你，敢接受这个挑战吗？</p>
<p><strong>补充说明：</strong></p>
<ul>
<li>求解两个 Flag 的过程都需要一定量的交互，为了在超时之前完成交互，建议批量发送数据后再批量接收数据。</li>
<li>拿到 3.3 不需要求出 Key，而只有求出 Key 才能拿到 4.0。</li>
</ul>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>第一个 Flag：找到经过 Base16 转换和添加 Padding 之后明文的字符集，算算它的大小，再计算出每个块有多少种可能的明文，看看适用什么样的攻击。</li>
<li>第二个 Flag：根据 Subkey 的特殊构造，可知用 <a target="_blank" rel="noopener noreferrer" href="https://en.wikipedia.org/wiki/Slide_attack">Slide Attack</a> 方法来攻击滑滑梯加密算法，请阅读该维基页面下方的论文，实现合适的 Slide Attack 变种，同时注意交互次数的限制。</li>
<li>题目环境的内存限制是 256MB，发送太长的数据（比如 100MB）可能导致程序崩溃，是正常现象。预期解仅需发送不超过 1MB 的数据。</li>
</ul>
</div>

**[【附件：下载题目源码（algo-slide.py）】](attachment/algo-slide.py)**

**【终端交互：连接到题目】**

## 预期解法

本题给了一个块加密算法，块大小为 4 字节，密钥大小为 6 字节。

### 第一个 Flag

首先观察简单模式，也就是第一个 Flag 的代码：

```python
plain = pad(base64.b16encode(flag_easy.encode()), 4)
enc_flag = encrypt(plain, key)
assert (
    decrypt(enc_flag, key) == plain
)
print(enc_flag.hex())
```

这里的主要问题是，采用 Base16 编码：经过 Base16 编码以后，字符集缩小到了 `[0-9A-F]`；即使经过了 pad，由于块大小是 4 字节，所以添加的 pad 只可能采用 `[\x01-\x04]` 这四种字节，合并起来，`plain` 的字符集也只有 20 个元素。考虑到每个块都是独立加密的（即 ECB 模式），并且明文的块只有 `20 ^ 4 = 160000` 种可能性，只需要枚举所有的可能性，发送给服务器，得到对应的密文，然后再根据密文反查加密后的 flag 即可。

考虑到选手机器到服务器之间有一定的延迟，所以采用批量发送的方式来加速交互：

```python
for batch in tqdm.tqdm(list(batched(itertools.product(alphabet, repeat=4), 128))):
    # send in batch
    p.sendline("".join(["".join(plain) for plain in batch]).encode().hex().encode())

    enc = bytes.fromhex(p.recvline().decode())
    assert len(enc) == 4 * len(batch)
    for i in range(len(batch)):
        plain = "".join(batch[i])
        mapping[enc[4 * i : 4 * (i + 1)]] = "".join(plain).encode()
```

攻击脚本见 [solve-easy.py](./sol/solve-easy.py)。

### 第二个 Flag

第二个 Flag 的代码通过 XOR 随机字节，并且控制交互次数，使得枚举明文不再可行：

```python
xor_key = token_bytes(len(flag_hard_padded))
scrambled = bytes(
    [a ^ b for a, b in zip(flag_hard_padded, xor_key)]
)

enc_scrambled = encrypt(scrambled, key)
enc_xor_key = encrypt(xor_key, key)
print(enc_scrambled.hex())
print(enc_xor_key.hex())
```

这时候就要回到加密算法的本身。上密码学课程的时候，老师一定会教我们，不要自己随意设计密码学算法，很可能已经有人设想出了类似的算法并提出了相应的攻击。本题涉及的滑滑梯加密算法，主要的问题在于它的 Key schedule，即 Subkey 的选择上：

```python
if mode == "e":
    round_key = keys[r % 2]
else:
    round_key = keys[
        (r + 1) % 2
    ]
```

也就是说，即使一共有 32 轮，但实际上只有两种 Subkey 轮流出现，也就是说，每两轮计算做的都是相同的变换。针对这种出现重复子结构的块加密算法，有一种现成的攻击方法叫做 [Slide Attack](https://en.wikipedia.org/wiki/Slide_attack)，事实上这个题的题面已经做了提示，为啥叫滑滑梯加密算法，因为滑梯的英文就是 Slide，提醒你用 Slide Attack 去攻击 Slide Cipher。

下面分析一下 Slide Attack 的思路：

1. 记使用到的两种 Subkey 为 Key0 和 Key1，那么滑滑梯加密算法做的事情就是用 `Key0, Key1, ..., Key1` 这个 Subkey 序列来进行加密
2. 服务器可以提供的交互是，输入任意一个块，输出这个块加密后的结果
3. 对任意一个明文 `P`，记它经过 32 轮加密后的结果为 `C`；假如已知 `Key0`，那么可以对 `C` 再进行一轮使用 Key0 为密钥的加密（注意处理交换），得到 `C'`，相当于是 `P` 经过 `Key0, Key1, ..., Key1, Key0` 这个 33 轮的 Subkey 序列进行加密的结果
4. 对 `C'` 进行完整 32 轮的加密（通过和服务器交互），由于 Feistel 结构的特点，加密和解密只有 Key 顺序的区别（注意处理交换），所以对 `C'` 进行加密，得到 `C''`，抵消了 32 轮的加密，得到的结果相当于 `P` 经过 `Key0` 进行一轮加密的结果
5. 在第三步的假设里，已知 `Key0`，又在第四步里得到了 `P` 经过 `Key0` 进行一轮加密的结果 `C''`，只需要再进行一轮的加密，就可以验证这个 `Key0` 是否合法
6. 因此只需要枚举 `Key0`，对每一个 `Key0` 都进行如上的操作，就可以找到合法的 `Key0`；有了 `Key0` 之后，再去搜索 `Key1` 即可
7. 但在这个过程中，每个 `Key0` 对应一次交互，就需要 `2 ^ 24` 次交互，超出了题目限制，因此需要想办法减少交互次数：注意到交互的内容，实际上是一个 4 字节的块，而且根据 Feistel 结构的特点，如果只做一轮加密，那么加密后的 `L` 等于明文的 `R`，那么只有加密后的 `R` 可能不同，那么交互的块的内容一共只有 `256 ^ 2 = 65536` 种可能，满足题目的交互要求

下面介绍一下大概的攻击过程：

1. 任意选定一个 `P`，发送给服务器，得到对应的密文 `C`
2. 枚举 `C'` 的 `256 ^ 2 = 65536` 种可能，发送给服务器，得到对应的 65536 个 `C''`，检查它与 `P` 是否构成加密后的 `L` 等于明文的 `R` 的关系（注意处理交换），筛选出合法的 `C''`
3. 从筛选出的合法的 `C''`，枚举 `Key0`，找到合法的 `Key0`；再根据合法的 `Key0` 枚举 `Key1`

攻击脚本见 [solve-hard.py](./sol/solve-hard.py)。
