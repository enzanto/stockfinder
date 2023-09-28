import requests
from bs4 import BeautifulSoup
import json
import requests
import re

session = requests.Session()
url_cookie = "https://www.investtech.com"
response = session.get(url_cookie)

cookie = session.cookies.get_dict()['sid']

with open('data/map.json', 'r') as mapfile:
    data = json.load(mapfile)
    tickers = data['stocks']


def get_img(ticker, cookie=cookie):

    url = "https://www.investtech.com/no/img.php"

    querystring = {"CompanyID":ticker['investechID'],"chartId":"2","indicators":"80,81,82,83,84,85,87,88","w":"1174","h":"515"}

    payload = ""
    headers = {
        "cookie": "sid="+cookie,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Cookie": "sid="+cookie+"; consent=all"
    }

    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

# image = requests.get(img_url)
    # return(response.content)
    with open("images/"+ticker['investechID']+".jpg", "wb") as f:
        f.write(response.content)

def get_text(ticker, cookie=cookie):
    url = "https://www.investtech.com/no/market.php"

    querystring = {"CompanyID":ticker['investechID']}

    payload = ""
    headers = {
        "cookie": "sid="+cookie,
        "Cookie": "sid="+cookie+"; consent=all",
    }

    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    soup = BeautifulSoup(response.text, 'html.parser')
    header = soup.find(string=re.compile('teknisk analyse'))
    body = soup.find('div', class_="ca2017_twoColCollapse")
    message = header + "\n" + body.text
    body = body.text.split(" ",9)[9]
    body = body.split("Anbefaling")[0]
    # print(body)
    return header,body
if __name__ == "__main__":    
    ticker = next(item for item in tickers if item['ticker'] == "fro.ol")
    print(ticker)
    get_img(ticker)
    header, message = get_text(ticker)
    print(message)
    # print(message[1].split("2023 ")[1])