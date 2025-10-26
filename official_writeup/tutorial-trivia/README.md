# [Tutorial] 北清问答

- 命题人：xmcp
- 𝓢𝓤𝓝𝓕𝓐𝓓𝓔𝓓：150 分
- ℂ𝕆ℕ𝕋ℝ𝔸𝕊𝕋：200 分

## 题目描述

<p>清北问答是上届 GeekGame 的经典题目，通过问答题的方式检验大家<strong>在互联网上查找、甄别、利用信息</strong>的能力。</p>
<p>遗憾的是，形势在今年发生了变化。专家发现，在直辖市的蜜雪冰城店铺附近的尖塔型建筑容易受到大地磁场的影响，向四周发射激光，对附近的电子设备产生干扰。这在具身智能领域被形象地称为 Oblivionis 现象。</p>
<p>由于 GeekGame 服务器位于北京大学理科一号楼内，容易受到附近蜜雪冰城（北京大学店）和尖塔形建筑（博雅塔）带来的 Oblivionis 影响，因此总是在比赛过程中出现神秘宕机事故。本题的名称也在高能粒子的轰击下不幸发生了比特翻转——具体来说，从【清北问答】变为【北清问答】，而且两处 Flag 名称的字体也产生了不规则扭曲。</p>
<p>总而言之，如果你甄别信息的能力足够，就能意识到：上面这些话是在一本正经地胡说八道，完全不需要看，<strong>正如其他题的题面大部分内容，都不需要看</strong>。只有后面这句话才是有用信息：</p>
<p>点击链接前往答题，<strong>答对一半题目</strong>可以获得 Flag 1，<strong>答对所有题目</strong>可以获得 Flag 2。</p>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>提交频率限制已放宽到 15 分钟一次。</li>
<li>2：这是 iPadOS 26 为 Liquid Glass 带来的新功能。</li>
<li>3：这是中国国航的航班，可以看看 <a target="_blank" rel="noopener noreferrer" href="https://seatmaps.com/airlines/ca-air-china/">国航所有机型的舱位图</a>。</li>
<li>5：可以看看 <a target="_blank" rel="noopener noreferrer" href="https://chromiumdash.appspot.com/branches">Chrome 正式版版本号对应的 branch</a>。如果你无法定位到精确 commit，可以找到大致的时间范围，然后多试试。</li>
<li>6：试试 <a target="_blank" rel="noopener noreferrer" href="https://netron.app/">Netron</a>。另外，请注意下载正确版本的模型文件（不要下载 turbo 版）。</li>
</ul>
</div>
**【网页链接：访问题目网页】**

## 预期解法

[在去年比赛的此题题面中](https://github.com/PKU-GeekGame/geekgame-4th/tree/master/official_writeup/misc-trivia)，清北问答声称要“检验选手在互联网上查找信息的能力”。一年过去，各家AI工具基本广泛支持了联网搜索功能，使得在合理使用的前提下，查找信息变得尤为方便。此处“合理使用”是指：

- 确保这个AI工具带联网搜索功能，而且真的会去搜索并使用搜索结果，而不是基于幻觉瞎编一些东西。
- 确保AI工具调用的搜索引擎是靠谱的，比如Gemini和Copilot显然就比文心一言和豆包更靠谱。
- 有能力验证AI工具的结论是否正确，以及在不正确的时候拷打它，或者至少忽略它的错误结果。
- 认识到AI工具的局限，比如如果一个任务需要编程才能解决，那就要用带执行命令功能的Agent。

因此，在利用AI查找信息的基础上，如何甄别和利用这些信息变得尤为重要。

下面将演示如何基于两个价格比较便宜的模型，Gemini 2.5 Flash（网页版，用于不需要编程的题目）和Kimi K2（在Agent中使用，用于需要编程的题目），来做出每个题目。

**点击跳转到对应Writeup：**

[北京大学新燕园校区的教学楼在启用时，全部教室共有多少座位（不含讲桌）？](sol/1.md)

答案格式：`\d+`，答案：2822

[基于 SwiftUI 的 iPad App 要想让图片自然延伸到旁边的导航栏（如右图红框标出的效果），需要调用视图的什么方法？](sol/2.md)

答案格式：`[a-z][A-Za-z0-9_]+`，答案：backgroundExtensionEffect


[右图这张照片是在飞机的哪个座位上拍摄的？](sol/3.md)

答案格式：`\d+[A-Z]`，答案：11K

[注意到比赛平台题目页面底部的【复制个人Token】按钮了吗？本届改进了 Token 生成算法，UID 为 1234567890 的用户生成的个人 Token 相比于上届的算法会缩短多少个字符？](sol/4.md)

答案格式：`\d+`，答案：11

[最后一个默认情况下允许安装 Manifest V1 .crx 扩展程序的 Chrome 正式版本是多少？](sol/5.md)

答案格式：`[4-9]\d`，答案：66

[此论文提到的 YOLOv12-L 目标检测模型实际包含多少个卷积算子？](sol/6.md)

答案格式：`\d{3}`，答案：212
