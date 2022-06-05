from flask import Flask, request, render_template
import json

from make_recipe import make_recipe_page
from make_shoppinglist import make_shoppinglist
from suumo2notion import suumo_update

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('button_template.html', uri='/execute')


@app.route('/execute')
def index_execute():
    return render_template('execute_template.html', text='実行完了')


@app.route('/suumo')
def suumo():
    return render_template('button_template.html', uri='/suumo_execute')


@app.route('/suumo_execute')
def suumo_execute():
    suumo_update()
    return render_template('execute_template.html', text='実行完了')


@app.route('/shoppinglist')
def shoppinglist():
    return render_template('button_template.html', uri='/shoppinglist_execute')


@app.route('/shoppinglist_execute')
def shoppinglist_execute():
    make_shoppinglist()
    return render_template('execute_template.html', text='実行完了')


# @app.route('/make_recipe', methods=['POST'])
# def make_recipe():
#     url = request.json['url']
#     make_recipe_page(url)
#     res = {'result': 'Success!'}
#     return json.dumps(res)


@app.route("/make_recipe", methods=["GET"])
def make_recipe():
    try:
        req = request.args
        url = req.get("url")
    except:
        res = {'result': 'parameter Error'}
    if url:
        make_recipe_page(url)
        res = {'result': 'Success!'}
    else:
        return render_template('make_menu_home.html')
    return json.dumps(res)


if __name__ == '__main__':
    app.run()
