import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
from get_key import *


def str2yen(t):
    nums = re.findall('\d+', t)
    if len(nums) == 1:
        num = int(nums[0])
    elif len(nums) > 1:
        num = int(nums[0]) + int(nums[1]) * 0.1 ** len(nums[1])
    else:
        return None

    if '万' in t:
        num = int(num * 10000)

    return num


def property2dict(elem):
    base_url = 'https://suumo.jp'
    tmp = {}

    content = elem.find(class_='property_inner-title').find('a')
    tmp['name'] = content.contents[0]
    tmp['url'] = base_url + content.attrs['href']

    content = elem.find("div", class_="detailnote").find(
        attrs={'style': 'font-weight:bold'})
    tmp['駅'] = content.contents[0].split('/')[1].split(' ')[0]
    tmp['駅徒歩'] = str2yen(content.contents[0])

    tds = elem.find('table').find_all('td')
    td = tds[0].find_all('div')
    tmp['家賃'] = str2yen(td[0].contents[0])
    tmp['管理費'] = str2yen(td[1].contents[0])
    td = tds[1].find_all('div')
    tmp['敷金'] = str2yen(td[0].contents[1])
    tmp['礼金'] = str2yen(td[1].contents[1])
    td = tds[2].find_all('div')
    tmp['間取り'] = td[0].contents[0]
    tmp['面積'] = str2yen(td[1].contents[0])
    tmp['向き'] = td[2].contents[0]
    td = tds[3].find_all('div')
    tmp['種別'] = td[0].contents[0]
    if '新築' in td[1].contents[0]:
        tmp['築年数'] = 0
    else:
        tmp['築年数'] = str2yen(td[1].contents[0])
    td = tds[4]
    tmp['所在地'] = td.contents[-1].split('\t')[-1]

    tmp['不動産'] = elem.find("a", class_="js-noCassetteLink").contents[0]
    try:
        tmp['間取り図'] = elem.find("li", id=re.compile(
            'js-madorizuImg*')).find('img').attrs['rel']
    except:
        tmp['間取り図'] = None
    return tmp


def pickup_content(value):
    endpoint_list = ['content', 'url', 'name', 'start']

    if type(value) == list:
        if len(value) == 1:
            return pickup_content(value[0])
        else:
            return [pickup_content(v) for v in value]
    elif type(value) == dict:
        if 'type' in value.keys():
            return pickup_content(value[value['type']])
        for endpoint in endpoint_list:
            if endpoint in value.keys():
                return pickup_content(value[endpoint])
        return value
    else:
        return value


def suumo_update():
    url = 'https://suumo.jp/jj/chintai/ichiran/FR301FC005/?ar=030&bs=040&smk=&po1=25&po2=99&shkr1=03&shkr2=03&shkr3=03&shkr4=03&rn=0185&ek=018523100&ra=013&cb=0.0&ct=9999999&md=04&md=05&md=06&md=07&ts=1&ts=2&et=10&mb=40&mt=9999999&cn=15&tc=0400101&fw2='
    pc = 100  # 同時表示件数（最大100件）
    page = 0

    prop_list = []
    page = 0
    i = 0
    while True:
        page += 1

        res = requests.get(f'{url}&pc={pc}&page={page}')
        soup = BeautifulSoup(res.content, "html.parser")
        elems = soup.find_all("div", class_="property")

        if len(elems) == 0:
            break
        for elem in elems:
            prop = property2dict(elem)

            prop_list.append(prop)
            i += 1
            print(i, prop['name'])

    df = pd.DataFrame(prop_list)
    df = df.replace('-', np.nan)

    database_id = '6e1a7863ac904ded83c47670b0324717'
    notion_version = "2022-02-22"
    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    payload = {"page_size": 100, "filter": {
        "property": "ステータス", "multi_select": {"does_not_contain": "終了"}}}
    headers = {
        "Accept": "application/json",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
        'Authorization': 'Bearer ' + notion_api_key
    }

    page_list = []
    next_cursor = 0
    while next_cursor != None:
        res = requests.post(url, json=payload, headers=headers)
        res = res.json()
        next_cursor = res['next_cursor']
        payload["start_cursor"] = next_cursor
        page_list += res['results']

    tmp_list = []
    for page in page_list:
        tmp = {}
        tmp['id'] = page['id']
        for key, value in page['properties'].items():
            tmp[key] = pickup_content(value)
        tmp_list.append(tmp)
    notion_df = pd.DataFrame(tmp_list)

    old_df = notion_df[~notion_df['url'].isin(df['url'])]

    properties = {'ステータス': {"multi_select": [{"name": "終了"}]}}
    post_data = {'properties': properties}

    for index, row in old_df.iterrows():
        url = f'https://api.notion.com/v1/pages/{row["id"]}'
        res = requests.patch(url, json=post_data, headers=headers)
        if res.status_code != 200:
            print(f'Error:{row["url"]}  {res.text}')
        else:
            print(f'deleted {row["name"]}')

    new_df = df[~df['url'].isin(notion_df['url'])]
    if len(new_df) > 0:
        new_prop_list = []
        j = 0
        for index, row in new_df.iterrows():
            prop = {}
            prop['url'] = row['url']
            res = requests.get(prop['url'])
            soup = BeautifulSoup(res.content, "html.parser")

            th_list = soup.find('table', class_='data_table').find_all('th')
            td_list = soup.find('table', class_='data_table').find_all('td')
            td_list = [td.get_text().replace(' ', '').replace(
                '\n', '').replace('\r', '').replace('\t', '') for td in td_list]
            th_list = [th.get_text() for th in th_list]
            for i in range(len(th_list)):
                if th_list[i] == '周辺情報' or th_list[i] == '携帯用QRコード':
                    continue
                prop[th_list[i]] = td_list[i]

            new_prop_list.append(prop)
            j += 1
            print(j, row['name'])
        add_df = pd.DataFrame(new_prop_list)
        new_df = new_df.merge(add_df)
        new_df = new_df.replace('-', np.nan)
        new_df['所在地'] = new_df['所在地'].str.replace('東京都立川市', '')
        new_df['総戸数'] = new_df['総戸数'].str.replace('戸', '').astype('float')
        new_df['SUUMO物件コード'] = new_df['SUUMO物件コード'].astype('int64')
        new_df['情報更新日'] = new_df['情報更新日'].str.replace('/', '-')

        prop_type = {"ステータス": "multi_select", "name": "title", "url": "url", "駅徒歩": "number", "面積": "number", "管理費": "number", "敷金": "number", "築年数": "number", "総戸数": "number", "礼金": "number", "家賃": "number", "SUUMO物件コード": "number", "駅": "select", "契約期間": "select", "取引態様": "select", "所在地": "select", "損保": "select", "次回更新日": "select", "向き": "select",
                     "構造": "select", "不動産": "select", "種別": "select", "間取り": "select", "間取り図": "files", "入居": "rich_text", "間取り詳細": "rich_text", "取り扱い店舗物件コード": "rich_text", "築年月": "rich_text", "駐車場": "rich_text", "ほか諸費用": "rich_text", "バルコニー面積": "rich_text", "階建": "rich_text", "備考": "rich_text", "仲介手数料": "rich_text", "条件": "rich_text", "保証会社": "rich_text", "情報更新日": "date"}

    new_df['ステータス'] = '新規'
    for index, row in new_df.iterrows():
        col_list = row[~row.isna()].index
        properties = {}
        for key, value in prop_type.items():
            if key not in col_list:
                continue
            if value == 'select':
                properties[key] = {"select": {"name": row[key]}}
            elif value == 'multi_select':
                properties[key] = {"multi_select": [{"name": row[key]}]}
            elif value == 'number':
                properties[key] = {"number": row[key]}
            elif value == 'rich_text':
                properties[key] = {"rich_text": [
                    {'text': {'content': row[key]}}]}
            elif value == 'url':
                properties[key] = {"url": row[key]}
            elif value == 'date':
                properties[key] = {"date": {"start": row[key], "end": None}}
            elif value == 'files':
                properties[key] = {
                    "files": [{"external": {"url": row[key]}, "name":row[key]}]}
            elif value == 'title':
                properties[key] = {'title': [{'text': {'content': row[key]}}]}
            else:
                print(f'{key}:{value} is not defined.')

        url = 'https://api.notion.com/v1/pages'
        post_data = {'parent': {'database_id': database_id},
                     'properties': properties}
        res = requests.post(url, json=post_data, headers=headers)
        if res.status_code != 200:
            print(f'Error:{row["url"]}  {res.text}')

    return 0
