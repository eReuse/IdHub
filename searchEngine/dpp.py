"""DPP"""

from json import loads
import httpx

categories = ['general']
paging = False
device=""

def resolve_inventory_url(id):
    r = httpx.get("http://45.150.187.47:3012/getURL?id="+id)
    print(r.text)
    return loads(r.text)['url']


def request(query, params):
    # query = urlencode({'query': query, 'c': (params['pageno'] - 1) * page_size})
    global device
    device = query
    chid = query.split(":")[0]
    #print(query)
    params['url'] = "http://45.150.187.47:3011/did:ereuse:" +chid
    return params


def response(resp):
    results = []
    #print(resp.text)
    json_results = loads(resp.text)['didDocument']

    for result in json_results['service']:
        if result['type'] == "DeviceHub":
            url = resolve_inventory_url(result['serviceEndpoint'])
            results.append({
                "url": url+"/dids/"+device,
                "title": device,
                "content": result['description'],
            })
    return results