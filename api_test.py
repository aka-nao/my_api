#%%
import requests
import json

#%%
url='http://127.0.0.1:5000'
r=requests.get(url)
print(r.text)

#%%
url='http://127.0.0.1:5000/post_test'
header={"Content-Type": "application/json"}
payload = {'key1': 'value1', 'key2': 10}

r=requests.post(url,data=json.dumps(payload),headers=header)
print(r.json())