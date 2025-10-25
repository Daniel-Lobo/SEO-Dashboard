from copy import deepcopy
from json import dumps
from flask import jsonify, request
from dashboard.app import g_, GetCurrentUserid, flask_templace
from requests import get
from os import getenv
from dashboard.ChatGpt import OpenRouterAChat

@g_.app.route('/RTNews-get', methods=["POST"])   
async def RTNews_get():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    country  = request.json["Country"]   #type: ignore
    kword    = request.json["Keyword"]   #type: ignore
    count    = request.json["Count"]     #type: ignore
    domain   = {'us' : 'google.com', 'ca' : 'google.ca', 'uk' : 'google.co.uk', 'au' : 'google.co.au', 'nl' : 'google.nl'}[country.lower()]   
    key      = getenv("VALUE_SERP_API_KEY")   
    url      = 'https://api.valueserp.com/search?news_type=blogs&time_period=last_week&sort_by=relevance&'
    request_string  = f'{url}api_key={key}&search_type=news&q={kword}&domain={domain}&gl={country}&hl=en&num={count}&location={country}'
    print(request_string)
    reply    = get(request_string).json()
    print(dumps(reply, indent=4))
    return jsonify({"Reply": reply['news_results']})

@g_.app.route('/RTNews-ideas', methods=["POST"])   #type: ignore 
async def RTNews_ideas():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    msgs     = request.json["Messages"]                          #type: ignore
    model    = request.json["Model"]                             #type: ignore
    user     = GetCurrentUserid()
    base_url = deepcopy(request.base_url)
    reply    = await OpenRouterAChat(msgs, model=model, temp=0.7, user=user, base_url=base_url)
    return jsonify({"Reply": reply})  #type: ignore
   