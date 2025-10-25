import json
from logging import exception
import anthropic
from flask import jsonify, request
from openai import ChatCompletion, api_key, api_key
from os import getenv
from aiohttp import ClientSession
from typing import cast

from dashboard.app import GetCurrentUserid
api_key            = getenv('OPENAI_API_KEY')
OPENROUTER_API_KEY = getenv('OPEN_ROUTER_KEY')
from json import dumps
from asyncio import sleep as async_sleep
api_base = "https://openrouter.ai/api/v1"
api_key  = OPENROUTER_API_KEY
from anthropic import AsyncAnthropic
from json import loads
from dashboard.alchemy import AlchemyLogs, postlog
from dashboard.app import g_, flask_templace
import logging

from google import genai
from google.genai import models as genai_models, types as genai_types
from google.genai.errors import APIError as GenaiAPIError

async def OpusAsyncChat(messages: list, temp=1., top_p=1.):
    client = AsyncAnthropic(api_key=getenv("ANTHROPIC_API_KEY"))
    print("==========================================, claude")
    user   = ''
    system = ''
    for message in messages:
        if   message['role']=='user'  : user = message['content']
        elif message['role']=='system': system = message['content']
    try:
        error = ''
        async with client.messages.stream(
            max_tokens  = 4096,
            system      = system,
            messages    = [
                {"role": "user", "content": user}
            ],
            temperature = temp,
            top_p       = top_p,
            model       = "claude-3-opus-20240229"
        ) as stream:
            async for event in stream:
               if event.type == 'error':
                   return str(event.data['error']['message'])
        assistant = loads((await stream.get_final_message()).to_json())
        print(assistant)              
        return assistant['content'][0]['text']      #type ignore
    except Exception as e:
        return f'Error calling OpenAI API: {str(e)}'            


async def ACompletion(prompt: str|list[str], model='gpt-4', temp=1., top_p=1.):
    try:
        if model=='gpt-4' : model='openai/gpt-4'
        messages = [{'role': 'user', 'content': prompt}] if isinstance(prompt, str) else [{'role': 'system', 'content': prompt[0]}, {'role': 'user', 'content': prompt[1]}]
        return await OpenRouterAChat(messages, model=model, temp=temp, top_p=top_p)
        '''
        response = await ChatCompletion.acreate(
            model       = model,            
            temperature = temp,
            top_p       = top_p,
            messages    = messages
        )
        '''
        return response.choices[0].message['content'].strip()  #type: ignore
    except Exception as e:
        return f'Error calling OpenAI API: {str(e)}'

async def AChat(messages: list, model='gpt-4', temp=1., top_p=1.):
    try:   
        if model=='gpt-4' : model='openai/gpt-4'   
        return await OpenRouterAChat(messages, model=model, temp=temp, top_p=top_p)
        '''  
        response = await ChatCompletion.acreate(
            model       = model,            
            temperature = temp,
            top_p       = top_p,
            messages    = messages
        )
        '''
        return response.choices[0].message['content'].strip()  #type: ignore
    except Exception as e:
        return f'Error calling OpenAI API: {str(e)}'

def TrimMessages(chat):   
    # chat_size = 3 x number_of_sections + 2 (current system and user prompts)    
    # a chat with more then 5 sections will have: 3 X 2 + 2 = 8 messages
    if len(chat) <= 11: return chat   
    timed_chat = chat[0:6]
    timed_chat.extend(chat[-5:])  
    return timed_chat

    '''
    # 5 sections
    if len(chat) <= 20: return chat   
    timed_chat = chat[0:3]
    timed_chat.extend(chat[-17:])  
    return timed_chat
    '''

async def GeminiAChat(messages: list, model, temp=1., top_p=1., max_tokens=0, tentative=1, 
                        user=None, base_url=None, dbug=False, grounding=False)->str:    
    print("============================GEMINI", model, "user", user)    
    import tiktoken
    import sys
    __messages = TrimMessages(messages)
    if dbug: return ''.join([msg['role'].upper() + ":\n" + msg['content'] + "\n" for msg in __messages])  

    tokens_count = 0
    encoding     = tiktoken.get_encoding("cl100k_base")
    for msg in __messages: tokens_count += len(encoding.encode(msg['content']))

    msgs   = [msg['content'] for msg in __messages]
    client = genai.Client(api_key=getenv('GEMMINI_API_KEY'))
    try:
        if grounding == False:
            response = await client.aio.models.generate_content(
                model     = model,
                contents  = msgs,
                config    = genai_types.GenerateContentConfig(
                    top_p = top_p,
                    temperature = temp,               
                )
            )
            print(response)
            return cast(str, response.text)
        else:
            response = await client.aio.models.generate_content(
                model     = model,
                contents  = msgs,
                config    = genai_types.GenerateContentConfig(
                    top_p = top_p,
                    temperature = temp,   
                    tools=[genai_types.Tool(google_search = genai_types.GoogleSearch())],
                    response_modalities=["TEXT"]          
                )
            )
            print(response)
            reply = ''
            if response.candidates is not None and len(response.candidates) > 0:
                if response.candidates[0].content is not None and response.candidates[0].content.parts is not None:
                    for each in response.candidates[0].content.parts:
                        if each.text is not None: reply += each.text
                    return reply
            return await \
            GeminiAChat(messages, model, temp, top_p, max_tokens, tentative, user, base_url, dbug, False)       
    except GenaiAPIError as e:
        if e.status == '429' and tentative < 5:
            return await \
            GeminiAChat(messages, model, temp, top_p, max_tokens, tentative+1, user, base_url, dbug, grounding)
    except Exception as e:
        return f'Error calling OpenAI API: {str(e)}'     
    return f'Error calling OpenAI API:'  # suppress pyright error


async def AnthropicAChat(messages: list, model, temp=1., top_p=1., max_tokens=0, _1st_try=True, user=None, base_url=None, dbug=False)->str:
    print("============================ANTHROPIC", model, "user", user)
    client = AsyncAnthropic(api_key=getenv("ANTHROPIC_API_KEY"))
    import tiktoken
    import sys
    __messages = TrimMessages(messages)
    if dbug: return ''.join([msg['role'].upper() + ":\n" + msg['content'] + "\n" for msg in __messages])  

    tokens_count = 0
    encoding     = tiktoken.get_encoding("cl100k_base")
    for msg in __messages: tokens_count += len(encoding.encode(msg['content']))
    caller       = str(sys._getframe(2).f_code.co_name) + ":" + str(sys._getframe(1).f_code.co_name)

    msgs = []
    for msg in __messages:
        msg['role'] = "user" if msg['role'] == 'user' else "assistant"
        msgs.append(msg)
   
    try:
        async with client.messages.stream(
            max_tokens  = 4096,            
            messages    = msgs,
            temperature = temp,
            top_p       = top_p,
            model       = model
        ) as stream:
            async for event in stream:
               if event.type == 'error':
                    if event['error ']['type'] == '**rate_limit_error**': 
                        time_to_wait = float(stream.response.headers['retry-after']) + 0.1
                        await async_sleep(time_to_wait)
                        return await AnthropicAChat(messages, model, temp=temp, top_p=top_p, max_tokens=max_tokens, _1st_try=False, user=user, base_url=base_url)
                    return str(event.data['error']['message'])
            assistant = loads((await stream.get_final_message()).to_json())
            #print(assistant)              
            return assistant['content'][0]['text']      #type ignore
    except anthropic.RateLimitError as e:
        time_to_wait = float(e.response.headers['retry-after']) + 0.1
        await async_sleep(time_to_wait)
        return await AnthropicAChat(messages, model, temp=temp, top_p=top_p, max_tokens=max_tokens, _1st_try=False, user=user, base_url=base_url)     
    except Exception as e:
        print(f"exception:", type(e), e)
        return f'Error calling OpenAI API: {str(e)}'
    

async def OpenRouterAChat(messages: list, model=None, temp=1., top_p=1., max_tokens=0, _1st_try=True, user=None, base_url=None, dbug=False)->str:

    if model == None: return f'Error calling Open Router API: no model specified, 1st try {_1st_try}'
    if model.endswith('🇦'): return await AnthropicAChat(messages, model.replace('🇦', ''), temp, top_p, 4096 if max_tokens==0 else max_tokens, _1st_try, user, base_url, dbug)
    if model.endswith('🇬'): 
        grounding = model.endswith('🇬 🇬')
        model     = model.replace('🇬 🇬', '').replace('🇬', '')
        return await \
        GeminiAChat(messages, model, temp, top_p, 4096 if max_tokens==0 else max_tokens, 1, user, base_url, dbug, grounding)

    import tiktoken    
    import sys
    print("==========================================,", sys._getframe(1).f_code.co_name, model, "user", user, "************")
    #msg = "==========================================," + str(sys._getframe(2).f_code.co_name) + "->" + str(sys._getframe(1).f_code.co_name) + " " + model + " user: " + user + " ************"
    #logging.warn(msg)
    #user = None
    if model.startswith('anthropic/claude-3-opus'): return await OpusAsyncChat(messages, temp, top_p)
    logger = AlchemyLogs()

    __messages = TrimMessages(messages)
    if dbug: return ''.join([msg['role'].upper() + ":\n" + msg['content'] + "\n" for msg in __messages])  

    #print(__messages[0]['content'])
    #print(__messages[1]['content'])
    tokens_count = 0
    encoding     = tiktoken.get_encoding("cl100k_base")
    for msg in __messages: tokens_count += len(encoding.encode(msg['content']))
    caller       = str(sys._getframe(2).f_code.co_name) + ":" + str(sys._getframe(1).f_code.co_name)

    json = {
                'model'       : model,
                'messages'    : TrimMessages(messages),
                'temperature' : float(temp),
                'top_p'       : top_p  
            }    
    try:               
        if max_tokens > 0: json |= {'max_tokens' : max_tokens}
        async with ClientSession() as session:
            async with session.post('https://openrouter.ai/api/v1/chat/completions',
                    headers = {
                        'Authorization': f'Bearer {OPENROUTER_API_KEY}', 
                        "HTTP-Referer":"https://dashboard.flawlessmarketing.com",
                        "X-Title":f"Flawless Dashboard:{caller}:{tokens_count}"
                        },
                    json = json
                    ) as response:
                log = json | {'status' : response.status, 'First try' : _1st_try}   
                print(response.status)               
                if response.status == 200: 
                    json = await response.json()               
                    try:       
                        log['Reply'] = json
                        #postlog(base_url, user, dumps(log, indent=4), msgtype='AI Request')
                        print("returnning")
                        return json['choices'][0]['message']['content'].strip()  #type: ignore  
                    except Exception as e: 
                        print(f"exception: {str(e)}")
                        return f'Error calling Open Router API: {str(e)}' + dumps(json)    
                elif response.status == 429:   
                    await async_sleep(1.1)
                    #postlog(base_url, user, dumps(log, indent=4), msgtype='AI Request')
                    return await OpenRouterAChat(messages, model, temp, top_p, max_tokens)
                #elif response.status == 408:                      
                    #return f'Timeout error calling Open Router API' 
                else:      
                    #postlog(base_url, user, dumps(log, indent=4), msgtype='AI Request')
                    if _1st_try==True: return await OpenRouterAChat(messages, model=model, temp=temp, top_p=top_p, max_tokens=max_tokens, _1st_try=False)                      
                    return f'Error calling Open Router API: Response.status == {response.status} calling Open Router API'                                    
    except Exception as e:
        print(f"exception: {str(e)}")
        log = json | {'Exception' : str(e), 'First try' : _1st_try}         
        if user != None: logger.log(user, dumps(log, indent=4), 'AI Request Exception')
        if _1st_try==True: return await OpenRouterAChat(messages, model=model, temp=temp, top_p=top_p, max_tokens=max_tokens, _1st_try=False) 
        return f'Error calling Open Router API: {str(e)}'

def RemoveXMLTags(reply):   
    try: reply = reply.split('<new>')[1].split('</new>')[0]
    except(IndexError): reply = reply    
    try: reply = reply.split('<content>')[1].split('</content>')[0]
    except(IndexError): reply = reply    
    return reply  

@g_.app.route("/chat-route", methods=['POST']) #type: ignore
async def ChatRoute():
    user   = GetCurrentUserid()
    if '' == user: return await flask_templace('login')    
    messages = request.json["Messages"]     #type: ignore
    model    = request.json["Model"]        #type: ignore
    temp     = request.json["Temperature"]  #type: ignore   
    return jsonify({'Assistant' : RemoveXMLTags(await OpenRouterAChat(messages, model=model, temp=temp))})

@g_.app.route("/check-credits", methods=['POST']) #type: ignore
async def GetCredits():
    openrouter_credits = 0
    openai_credits     = 0
    anthropic_credits  = 0
    async with ClientSession() as session:
        async with session.get('https://openrouter.ai/api/v1/auth/key',
                headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'}
                ) as response:
                print(dumps(await response.json(), indent=4))
                if response.status == 200: 
                    openrouter_credits = (await response.json())['data']['limit_remaining']  
    return jsonify({'openrouter': openrouter_credits, 'openai': openai_credits, 'anthropic': anthropic_credits})  #type: ignore                                            
    async with ClientSession() as session:
        async with session.get('https://api.openai.com/v1/usage',
                headers = {"Authorization" : f'Bearer{getenv("OPENAI_API_KEY")}'}
                ) as response:
                print(response)
                if response.status == 200: 
                    openai_credits = (await response.json())['data'][0]['usage']      
    return jsonify({'openrouter': openrouter_credits, 'openai': openai_credits, 'anthropic': anthropic_credits})  #type: ignore 


@g_.app.route("/list-anthropic-models", methods=['POST']) #type: ignore
async def GetAnthropicModels():
    """Get available models from Anthropic API using official client"""
    try:
        # Initialize the Anthropic client
        client = AsyncAnthropic(api_key=getenv("ANTHROPIC_API_KEY"))
        
        # Get the list of models
        response = await client.models.list() 
        
        # Format the model information
        models = [{
            'id'   : model.id,
            'name' : model.display_name,            
        } for model in response.data]
        
        return jsonify({"Err" : "S_OK", 'Models': models})
    except Exception as e:
        return jsonify({"Err": f"Error fetching Anthropic models: {str(e)}"}), 500       

@g_.app.route("/list-google-models", methods=['POST']) #type: ignore
async def GetGoogleModels():
    client = genai.Client(api_key=getenv('GEMMINI_API_KEY'))
    models = await client.aio.models.list(config={'page_size': 500})
    models_list = \
    [{'id' : model.name, 'name' : model.display_name} for model in models.page if model.supported_actions != None and "generateContent" in list(model.supported_actions)]
    print([model.supported_actions for model in  models.page])
    return jsonify({'Models': models_list})
   