import subprocess, json, os, sys, random, threading
# import gevent.monkey
# gevent.monkey.patch_all()
import eel
from pathlib import Path
path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))
# print(sys.path)
# print(path_root)
from ereuseapi.methods import API, register_user

port = 8000
mode = 'chrome'

# print(sys.argv)

def check_arg(index):
    global mode
    global port
    if sys.argv[index]=="-m":
        if sys.argv[index+1] == "None": mode = None
        else: mode = sys.argv[index+1]
    elif sys.argv[index]=="-p":
        port = int(sys.argv[index+1])
    else: raise

try:    
    if len(sys.argv)> 1:
        check_arg(1)
    if len(sys.argv)> 3:
        check_arg(3)
except:
    print("Flags:\n -p <port>\n -m <browser> (browser options: chrome, electron, edge, None) (Any other string will open the default system browser.)")
    exit()


# print(f"Name: {__name__}")
# print(f"Package: {__package__}")

eel.init('web')

api_object = None
# api_object = API("http://localhost:3010", "Q91PbwYAwjIF1vB.38CjhblT7NnwMFuNOEpWNdZonB0yWMkrRhGglVr7qMD6Iqbzep0hJYIz7IRprNku", "ethereum")
# func = getattr(api_object, "issue_credential")
# print(func)

@eel.expose
def read_endpoints():
    f = open("web/endpoints.json")
    data = json.load(f)
    f.close()
    print("endpoints read")
    return data

@eel.expose
def read_sections():
    f = open("web/sections.json")
    data = json.load(f)
    f.close()
    print("sections read")
    return data

@eel.expose
def read_dlts():
    f = open("web/dlts.json")
    data = json.load(f)
    f.close()
    print("dlts read")
    return data

@eel.expose
def init_api_object(endpoint, key, dlt):
    global api_object 
    api_object = API(endpoint,key,dlt)
    # print(dlt)
    # print(api_object.dlt)

@eel.expose
def register_new_user(endpoint):
    print("generating key")
    key = register_user(endpoint)['data']['api_token']
    print(key)
    return key

@eel.expose
def call_api(method, args):
    print(method)
    print(args)
    if method == "register_user":
        result = register_user(api_object.api_endpoint)
    else:
        func = getattr(api_object, method)
        result = func(*args)
    return result

eel.start('main.html', size=(1000, 800), mode=mode, port=port)
