import urllib.request, urllib.error
from urllib.request import urlopen as _url_open
req = urllib.request.Request('http://127.0.0.1:8000/v3/web/status', method='GET')
try:
    print(_url_open(req).getcode())
except urllib.error.HTTPError as e:
    print(e.code)
