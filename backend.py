import requests
import random
import json
""" key="https://zenquotes.io/api/random"
bad quotes bruhhh


res=requests.get(key)

data=res.json()
 no=random.randint(0,10)
print(no)
print(f"{data[0].get('q')} ------------------- {data[0].get('a')} ") """




def quotes():
    filep="quotes.json"
    with open(filep,"r") as w:
        data=json.load(w)

    rand=random.randint(0,49)
    text=data[rand].get('text')
    by=data[rand].get('author')
    return text,by
    



