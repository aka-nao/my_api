# %%
import requests
import datetime
from get_key import *

database_id = 'f5721cc0463f4586b7d2aa4a69577113'
notion_version = "2022-02-22"
headers = {
    "Accept": "application/json",
    "Notion-Version": notion_version,
    "Content-Type": "application/json",
    'Authorization': 'Bearer ' + notion_api_key
}


# %%
def get_menu_list():
    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    payload = {"page_size": 100, "filter": {"and": [{"property": "買い出し済", "checkbox": {
        "equals": False}}, {"property": "メニュー", "relation": {"is_not_empty": True}}]}}
    page_list = []
    next_cursor = 0
    while next_cursor != None:
        res = requests.post(url, json=payload, headers=headers)
        res = res.json()
        next_cursor = res['next_cursor']
        payload["start_cursor"] = next_cursor
        page_list += res['results']

    menu_list = []
    for page in page_list:
        menu_dict = {}
        name = page['properties']['Name']['title']
        if len(name) == 0:
            menu_dict['name'] = None
        else:
            menu_dict['name'] = name[0]['text']['content']
        menu_dict['page_id'] = page['id']
        menu_dict['title'] = page['properties']['メニュー名']['rollup']['array'][0]['title'][0]['text']['content']
        menu_dict['itg_list'] = [x['name'] for x in page['properties']
                                 ['材料:分量']['rollup']['array'][0]['multi_select']]
        menu_list.append(menu_dict)

    return menu_list


# %%
def make_shoppinglist():
    menu_list = get_menu_list()

    url = 'https://api.notion.com/v1/pages'
    children = []
    for menu in menu_list:
        itg_list = []
        for itg in menu['itg_list']:
            itg_list.append({'object': 'block', 'type': 'to_do', 'to_do': {
                            'rich_text': [{'type': 'text', 'text': {'content': itg}}]}})
        children.append({'object': 'block', 'type': 'bulleted_list_item', 'bulleted_list_item': {'rich_text': [
                        {'type': 'text', 'text': {'content': menu['title']}}], "children": itg_list}})

    properties = {'Name': {'title': [{'text': {'content': '買い出しリスト'}}]}, "Date": {
        "date": {"start": datetime.datetime.now().strftime("%Y-%m-%d")}}}

    post_data = {'parent': {'database_id': database_id},
                 'properties': properties, 'children': children}
    res = requests.post(url, json=post_data, headers=headers)
    if res.status_code != 200:
        print(f'Error:{url} {res.text}')
    else:
        print(f'{url} : OK!')
        for menu in menu_list:
            if menu['name'] is None:
                name = menu['title']
            else:
                name = menu['name']
            post_data = {"properties": {"買い出し済": {"checkbox": True},
                                        "Name": {'title': [{'text': {'content': name}}]}}}
            url = f'https://api.notion.com/v1/pages/{menu["page_id"]}'
            res = requests.patch(url, json=post_data, headers=headers)
            if res.status_code != 200:
                print(f'Error:{url} {res.text}')
            else:
                print(f'{url} : OK!')

# %%
