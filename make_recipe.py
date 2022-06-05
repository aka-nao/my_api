import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
from urllib.parse import urlparse
import pykakasi
import neologdn

from get_key import *

kks = pykakasi.kakasi()
kks.setMode('J', 'K')
kks.setMode('H', 'K')
conv = kks.getConverter()

main_ingredients = pd.read_excel(ingredients_file_path, sheet_name='Sheet1')
main_ingredients['encoded'] = main_ingredients['encoded'].map(eval)
main_ingredients = main_ingredients[['name', 'type']].merge(
    main_ingredients['encoded'].explode(), left_index=True, right_index=True)


def del_waste(text):
    pattern = '\(|\)|（|）|【|】|\s'
    text = re.sub(pattern, '', text)
    return text


def format_text(text):
    text = neologdn.normalize(text)
    return text


def katakana(text):
    text = conv.do(text)
    return text


def del_kakko(text):
    text = re.sub("(\(|（).*(\)|）)", "", text)
    return text


def get_main_ingredients(ingredient):
    ingredient = format_text(del_kakko(katakana(ingredient)))
    tmp = main_ingredients[main_ingredients['encoded'] == ingredient]
    if len(tmp) == 0:
        return None
    elif len(tmp) == 1:
        return tmp['name'].item()
    else:
        print(tmp)
        return tmp['name'][0].item()


url = 'https://www.irisohyama.co.jp/kitchen/cooker/recipe/3l/recipe03/'


def scraping_iris(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    res = {'url': url}
    res['title'] = soup.select_one('h3').text

    try:
        res['cooking_time'] = soup.select_one(
            '.cooking-time').select_one('h4').text.split('：')[-1]
    except:
        pass

    res['serving_num'] = soup.select_one('.ingredient').select_one(
        'h4').text.split('：')[-1].split('　')[-1]
    img_src = soup.select_one('.dish-photo')['src']
    if img_src[:3] == '../':
        res['image'] = os.path.join(url, img_src)
    else:
        res['image'] = os.path.join(url, '../', img_src)

    try:
        recipe_table = soup.select_one(
            '.recipe-table').select_one('.list-clm2')
    except:
        recipe_table = soup.select_one('.recipe-info')
        if not recipe_table:
            recipe_table = soup.select_one('.list-clm2')
    try:
        res['calorie'] = [d.text for t, d in zip(recipe_table.select(
            'dt'), recipe_table.select('dd')) if 'カロリー' in t.text][0]
    except:
        pass

    ingredients = soup.select_one('.ingredient').select_one('.list-clm2')
    dt_list = [t.text.replace('・', '') for t in ingredients.select(
        'dt') if not (t.has_attr('class'))]
    res['ingredients'] = {t: d.text for t, d in zip(
        dt_list, ingredients.select('dd')) if len(del_waste(d.text)) > 0}

    return res


url = 'https://cookpad.com/recipe/2395372'


def scraping_cookpad(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.select_one(
        '#recipe-title').select_one('h1').text.replace('\n', '')
    image = soup.select_one(
        '#main-photo').select_one('img')['src'].split('?')[0]
    ingredients = soup.select_one('#ingredients')
    serving_num = del_waste(ingredients.select_one(
        '.recipe_heading').select('span')[-1].text)
    ingredients_list = soup.select_one('#ingredients_list')
    ingredient_name = [x.select_one(
        'span').text for x in ingredients_list.select('.ingredient_name')]
    ingredient_quantity = [
        x.text for x in ingredients_list.select('.ingredient_quantity')]
    ingredients = {ingredient_name[i]: ingredient_quantity[i]
                   for i in range(len(ingredient_name))}

    res = {'url': url, 'title': title, 'image': image,
           'serving_num': serving_num, 'ingredients': ingredients}
    return res


url = 'https://www.kurashiru.com/recipes/969cccfc-a4fc-4c27-8fc7-ed1608c05c03'


def scraping_kurashiru(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.select_one('.title').text.replace('　レシピ・作り方', '')
    image = soup.select_one('video')['poster']
    cooking_time = soup.select_one(
        '.cooking-time').text.split('：')[-1].split('\n')[0]
    expense = soup.select_one('.expense').text.split('：')[-1].split('\n')[0]
    ingredients_block = soup.select_one('.ingredients')
    serving_num = del_waste(ingredients_block.select_one('.servings').text)

    ingredients = {}
    for integ in ingredients_block.select('.ingredient-list-item'):
        if integ.select_one('.ingredient-title'):
            continue
        name = integ.select_one(
            '.ingredient-name').text.replace('\n', '').replace(' ', '')
        amount = integ.select_one(
            '.ingredient-quantity-amount').text.replace('\n', '').replace(' ', '')
        ingredients[name] = amount

    res = {'url': url, 'title': title, 'image': image, 'cooking_time': cooking_time,
           'cost': expense, 'serving_num': serving_num, 'ingredients': ingredients}
    return res


url = 'https://www.sirogohan.com/recipe/takenokogohan/'


def scraping_sirogohan(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.select_one('#recipe-name').text.replace('のレシピ/作り方', '')
    image = soup.select_one('#recipe-main').select_one('img')['src']
    cooking_time = soup.select_one('#cooking-time').contents[0].split('：')[-1]
    try:
        serving_num = del_waste(soup.select_one(
            '.material-ttl').select_one('span').text)
    except:
        serving_num = ''

    ingredients = {}
    for integ in sum([c.select('li') for c in soup.select('.material-halfbox')], []):
        tmp = integ.text.split('…')
        ingredients[tmp[0]] = tmp[1].replace('　', '')

    res = {'url': url, 'title': title, 'image': image, 'cooking_time': cooking_time,
           'serving_num': serving_num, 'ingredients': ingredients}
    return res


url = 'https://delishkitchen.tv/recipes/232432811104011364'


def scraping_delishkitchen(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.select_one('.title').text
    image = soup.select_one('video')['poster'].split('?')[0]
    cooking_time = soup.select_one('.time-text').text
    calorie = soup.select('.calorie-item')[1].text
    serving_num = del_waste(soup.select_one(
        '.recipe-serving').select_one('span').text)
    calorie = f'{calorie}/{serving_num}'

    ingredients = {}
    for integ in soup.select('.ingredient'):
        name = integ.select_one('.ingredient-name').text
        amount = integ.select_one('.ingredient-serving').text
        ingredients[name] = amount

    res = {'url': url, 'title': title, 'image': image, 'cooking_time': cooking_time,
           'calorie': calorie, 'serving_num': serving_num, 'ingredients': ingredients}
    return res


url = 'https://macaro-ni.jp/108789'


def scraping_macaroni(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.select_one('.articleInfo__title').text
    try:
        image = soup.select_one('video')['poster'].split('?')[0]
    except:
        image = ''

    calorie = None
    for c in soup.select('.articleShow__nutritionList'):
        if c.select_one('.articleShow__nutritionLabel').text == 'エネルギー':
            calorie = c.select_one('.articleShow__nutritionValue').text
            calorie = f'{calorie}/1人分'

    serving_num = del_waste(soup.select_one(
        '.articleShow__contentsMaterialHeading').contents[-1])

    ingredients = {}
    for integ in soup.select('.articleShow__contentsMateriialItem'):
        name = integ.select_one('.articleShow__contentsMaterialName').text
        amount = integ.select_one('.articleShow__contentsMaterialAmout').text
        ingredients[name] = amount

    res = {'url': url, 'title': title, 'image': image,
           'serving_num': serving_num, 'ingredients': ingredients}
    if calorie:
        res['calorie'] = calorie
    return res


def get_recipe(url):
    netloc = urlparse(url).netloc

    if netloc == 'www.irisohyama.co.jp':
        recipe = scraping_iris(url)
    elif netloc == 'cookpad.com':
        recipe = scraping_cookpad(url)
    elif netloc == 'www.kurashiru.com':
        recipe = scraping_kurashiru(url)
    elif netloc == 'www.sirogohan.com':
        recipe = scraping_sirogohan(url)
    elif netloc == 'delishkitchen.tv':
        recipe = scraping_delishkitchen(url)
    elif netloc == 'macaro-ni.jp':
        recipe = scraping_macaroni(url)
    else:
        print('not found')
        return {}

    return recipe


def get_properties(target):
    recipe_properties = {'url': {'name': 'URL', 'type': 'url'},
                         'title': {'name': 'メニュー', 'type': 'title'},
                         'image': {'name': '画像', 'type': 'files'},
                         'cooking_time': {'name': '調理時間', 'type': 'rich_text'},
                         'serving_num': {'name': '分量', 'type': 'rich_text'},
                         'calorie': {'name': 'カロリー', 'type': 'rich_text'},
                         'cost': {'name': '費用', 'type': 'rich_text'},
                         'ingredients': {'name': '材料:分量', 'type': 'multi_select'},
                         'main_ingredients': {'name': '主な食材', 'type': 'multi_select'}}

    properties = {}
    for key, value in target.items():
        propertie_info = recipe_properties[key]
        if propertie_info['type'] == 'title':
            properties[propertie_info['name']] = {
                'title': [{'text': {'content': value}}]}
        elif propertie_info['type'] == 'select':
            properties[propertie_info['name']] = {"select": {"name": value}}
        elif propertie_info['type'] == 'multi_select':
            properties[propertie_info['name']] = {
                "multi_select": [{"name": v} for v in value]}
        elif propertie_info['type'] == 'number':
            properties[propertie_info['name']] = {"number": value}
        elif propertie_info['type'] == 'rich_text':
            properties[propertie_info['name']] = {
                "rich_text": [{'text': {'content': value}}]}
        elif propertie_info['type'] == 'url':
            properties[propertie_info['name']] = {"url": value}
        elif propertie_info['type'] == 'date':
            properties[propertie_info['name']] = {
                "date": {"start": value, "end": None}}
        elif propertie_info['type'] == 'files':
            properties[propertie_info['name']] = {
                "files": [{"external": {"url": value}, "name": value[:100]}]}
        else:
            print(f'{key}:{value} is not defined.')
    return properties


def make_recipe_page(url):
    database_id = 'f1eef3a31024437ead54a7198aac80b3'
    notion_version = "2022-02-22"
    headers = {
        "Accept": "application/json",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
        'Authorization': 'Bearer ' + notion_api_key
    }

    recipe = get_recipe(url)
    tmp = [get_main_ingredients(key) for key in recipe['ingredients'].keys()]
    recipe['main_ingredients'] = [x for x in tmp if x is not None]
    recipe['ingredients'] = [f'{k}:{v}' for k,
                             v in recipe['ingredients'].items()]
    properties = get_properties(recipe)

    url = 'https://api.notion.com/v1/pages'
    post_data = {'parent': {'database_id': database_id},
                 'properties': properties,
                 "cover": {"type": "external", "external": {"url": recipe['image']}}
                 }
    res = requests.post(url, json=post_data, headers=headers)
    if res.status_code != 200:
        print(f'Error:{url} {res.text}')
    else:
        print(f'{url} : OK!')
