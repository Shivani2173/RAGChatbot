import json
from bs4 import BeautifulSoup

html = open('data/raw/groww_value_fund.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'lxml')
script = soup.find('script', id='__NEXT_DATA__')
data = json.loads(script.string)

def find_keys(obj, path=""):
    if isinstance(obj, dict):
        if 'expense_ratio' in obj:
            print(f"Found expense_ratio at {path} -> {obj['expense_ratio']}")
        if 'benchmark' in obj or 'benchmark_name' in obj:
            print(f"Found benchmark at {path} -> {obj.get('benchmark') or obj.get('benchmark_name')}")
        for k, v in obj.items():
            find_keys(v, path + "." + k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            find_keys(item, path + f"[{i}]")

find_keys(data)
