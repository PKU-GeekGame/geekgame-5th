from dataclasses import dataclass
from random import random, randint, choice, shuffle
from string import ascii_letters, digits

schema_types = []
name_set = set([''])

KCTD_PRESET = '103765749452800'

@dataclass
class Field:
    name: str
    type: str
    value: str

CHARSET = ascii_letters + digits
def get_name() -> str:
    name = ''
    while name in name_set:
        name = ''.join(choice(CHARSET) for _ in range(4))
    name_set.add(name)
    return name

def gen(max_depth: int, flag: bool, root = False) -> Field:
    if max_depth == 0:
        if flag:
            return Field('flag2', 'String', 'FLAG2')
        scalar = randint(0, 3)
        name = f'not_flag_{get_name()}'
        if scalar == 0:
            return Field(name, 'Int', str(randint(0, 99)))
        if scalar == 1:
            return Field(name, 'Float', f'{random():.2f}')
        if scalar == 2:
            return Field(name, 'Boolean', choice(['True', 'False']))
        return Field(name, 'String', f'"{choice(CHARSET)}"')

    type = 'Secret' if root else f'Secret_{get_name()}'
    name = f'secret_{get_name()}'

    children_count = randint(4, 5)
    flag_child = randint(0, children_count - 1) if flag else -1
    children = [
        gen(max(0, max_depth - (1 if i == flag_child else randint(1, 2))), i == flag_child)
        for i in range(children_count)
    ]

    if root:
        schema_types.append(f'''type NotPartOfChallenge {{
  selectOnePresetData(presetKey: String!, XH: String!, KCH: String!): Preset{KCTD_PRESET}
  formParser(status: String!, presetbind: String!, XH: String!, KCH: String!): Preset{KCTD_PRESET}
}}

type Preset{KCTD_PRESET} {{
  msg: String
  status: String
  XH: String
  KCH: String
  KSRQ: String
  XNXQ: String
  XF: Int
  KCMC: String
  ZCJ: Int
}}''')
        children.append(Field(
            'not_part_of_challenge',
            'NotPartOfChallenge',
            '{ "selectOnePresetData": selectOnePresetData, "formParser": formParser }'
        ))

    children_schema = '\n  '.join(map(lambda c: f'{c.name}: {c.type}', children))
    schema_types.append(f'''type {type} {{
  {children_schema}
}}''')

    children_value = ','.join(map(lambda c: f'"{c.name}":{c.value}', children))
    value = f'{{{children_value}}}'

    return Field(name, type, value)

root = gen(8, True, True)
shuffle(schema_types)

with open('secret.gql', 'w') as f:
    f.write('\n\n'.join(schema_types))

with open('secret_handler.py', 'w') as f:
    f.write(f'''import re

try:
    with open('/flag2') as f:
        FLAG2 = f.read().strip()
except:
    FLAG2 = 'fake{{dummy_flag2}}'

def kctd(XH: str, KCH: str):
    if re.match(r'^20\\d{{8}}$', XH) is None or re.match(r'^\\d{{8}}$', KCH) is None:
        return {{ 'msg': '未查询到结果!', 'status': 'error' }}
    return {{
        'XH': XH,
        'KCH': KCH,
        'KSRQ': "20251024",
        'XNXQ': "2025-2026-1",
        'XF': int(KCH[-1]),
        'KCMC': '2025 “京华杯” 信息安全综合能力竞赛',
        'ZCJ': -99,
    }}

def selectOnePresetData(info, presetKey: str, XH: str, KCH: str):
    if presetKey != '{KCTD_PRESET}':
        return {{ 'msg': '基础数据不存在或无权访问!', 'status': 'error' }}
    return kctd(XH, KCH)

def formParser(info, status: str, presetbind: str, XH: str, KCH: str):
    if status != 'preset' or presetbind != '{KCTD_PRESET}':
        return None
    return kctd(XH, KCH)

def secret_handler():
    return {root.value}
''')
