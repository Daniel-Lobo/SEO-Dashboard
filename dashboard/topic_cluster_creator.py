from os import getenv
from dashboard.constants import PROMPT
from dashboard.ChatGpt import ACompletion, OpenRouterAChat #type: ignore
from openai import ChatCompletion 
from json import loads
from aiohttp import ClientSession
OPENROUTER_API_KEY = getenv('OPEN_ROUTER_KEY')
from json import dumps
from asyncio import sleep as async_sleep
from typing import List, cast
                    
async def GenFacts(kword, model, system, user):
    print('Generatin facts for keyword: ', kword)
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    return await OpenRouterAChat(messages, model=model, temp=0.1)

async def GenerateEntities(kword: str, model, prompts: dict):
    try:
        promtps  = [prompts['Generation'], kword]
        ai_reply = await ACompletion(promtps, model=model, temp=0.2)        
        ent      = ai_reply.split('Contextual Frame')[0].split('Core Entity:')[1].strip()
        cntx     = ai_reply.split('Contextual Frame:')[1].strip()
        return {'CoreEntity' : ent, 'ContextualFrame' : cntx, 'Keyword' : kword}
    except Exception as e:    
        return {'CoreEntity' : f'Exception {e}', 'ContextualFrame' : f'Exception {e}', 'Keyword' : kword}

async def EntityAnalysisF(ent, cntx, kword):
    prompt  = PROMPT.ENTITY_ANALISYS_PROMPT.format(ent, cntx, kword)
    messages = [{'role': 'user', 'content': prompt}]
    try:
        response = await ChatCompletion.acreate(
            headers={},
            model='gpt-4', temperature=0.2, top_p=0.7, messages=messages,            
            tools = [
                {
                    'type': 'function',
                    'function': {
                        'name': 'entitly_analisys_results', 
                        'description' : 'enumerate entitly analisys results',                  
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'Nouns': {
                                    'type': 'string',                                
                                },                               
                                'Subject-Object-Predicates': {
                                    'type': 'string',                                
                                }, 
                                'Searcher Considerations': {
                                    'type': 'string',                                
                                },    
                                'Attributes': {
                                    'type': 'string',                                
                                },                                  
                                'Characteristics': {
                                    'type': 'string',                                
                                }, 
                                'Semantic Relationships': {
                                    'type': 'string',                                
                                },                                                                                     
                            },
                            'required': ['Nouns', 'Subject-Object-Predicates', 'Searcher Considerations', 'Attributes', 
                             'Characteristics', 'Semantic Relationships'],
                        },
                    },
                }
            ]
        )
        result = ''
        args_dict = loads(response['choices'][0]['message']['tool_calls'][0]['function']['arguments']) #type: ignore
        for key, arg in args_dict.items():
            result += f'{key}: {arg.lower()}\n\n'
        return result.strip()
    except Exception as e:
        print(str(e))
        msg = f'Error calling OpenAI API: {e}'      
        return msg   


def GetTextBetwenTags(text, tag):
    start_tag = f'<{tag}>'
    end_tag   = f'</{tag}>'
    try:
        return text.split(start_tag)[1].split(end_tag)[0]
    except:
        return '' 

async def EntityAnalysisOtherProviders(ent, cntx, kword, model, prompts): 
    messages = [
    {
        'role': 'user',   
        'content': prompts['Analysis-User'].replace('{CORE_ENTITY}', ent).replace('{CONTEXTUAL_FRAME}', cntx).replace('{KEYWORD}', kword)},
    {
        'role': 'system', 
        'content': prompts['Analysis-System'].replace('{CORE_ENTITY}', ent).replace('{CONTEXTUAL_FRAME}', cntx).replace('{KEYWORD}', kword)
    }
    ]
    reply                  = await OpenRouterAChat(cast(List, messages), model=model, temp=0.2)
    semantic_relationships = GetTextBetwenTags(reply, 'semantic-relationships')
    analisys = f'Nouns: {GetTextBetwenTags(reply, "nouns")}\n' + \
            f'Subject-Object-Predicates: {GetTextBetwenTags(reply, "predicates")}\n' + \
            f'Searcher Considerations: {GetTextBetwenTags(reply, "searcher-considerations")}\n' + \
            f'Attributes: {GetTextBetwenTags(reply, "attributes")}\n' + \
            f'Characteristics: {GetTextBetwenTags(reply, "characteristics")}\n' + \
            f'Semantic Relationships:\nsynonyms: {GetTextBetwenTags(semantic_relationships, "synonyms")}\n' + \
            f'related concepts: {GetTextBetwenTags(semantic_relationships, "related-concepts")}\n' 
    return analisys

async def EntityAnalysisOpenRouter(ent, cntx, kword, model, prompts, _1st_try=True):
    try:
        if not model.startswith('openai/'): return await EntityAnalysisOtherProviders(ent, cntx, kword, model, prompts)
        #prompt  = PROMPT.ENTITY_ANALISYS_PROMPT.format(ent, cntx, kword)        
        prompt   = prompts['Analysis-OpenAI'].replace('{CORE_ENTITY}', ent).replace('{CONTEXTUAL_FRAME}', cntx).replace('{KEYWORD}', kword)
        messages = [{'role': 'user', 'content': prompt}]
        json = {
                'model'       : model,
                'messages'    : messages,  
                'temperature' : 0.2,              
                'tools' : [
                    {
                    'type': 'function',
                    'function': {
                        'name': 'entitly_analisys_results', 
                        'description' : 'enumerate entitly analisys results',                  
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'Nouns': {
                                    'type': 'string',                                
                                },                               
                                'Subject-Object-Predicates': {
                                    'type': 'string',                                
                                }, 
                                'Searcher Considerations': {
                                    'type': 'string',                                
                                },    
                                'Attributes': {
                                    'type': 'string',                                
                                },                                  
                                'Characteristics': {
                                    'type': 'string',                                
                                }, 
                                'Semantic Relationships': {
                                    'type': 'string',                                
                                },                                                                                     
                            },
                            'required': ['Nouns', 'Subject-Object-Predicates', 'Searcher Considerations', 'Attributes', 
                             'Characteristics', 'Semantic Relationships'],
                        },
                    },
                }
            ]
        }

        async with ClientSession() as session:
            async with session.post('https://openrouter.ai/api/v1/chat/completions',
                    headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                    json = json
                    ) as response:
                if response.status == 200: 
                    json = await response.json()  
                elif response.status == 429:   
                    await async_sleep(1.1)
                    return await EntityAnalysisOpenRouter(ent, cntx, kword, model, prompts)                    
                else:   
                    if _1st_try == True: return await EntityAnalysisOpenRouter(ent, cntx, kword, model, prompts, _1st_try=False)                          
                    return f'Error calling Open Router API: Response.status == {response.status} calling Open Router API'    
       
        #print(dumps(json, indent=4))
        result = ''
        if model.startswith('openai/'):
            args_dict = loads(json['choices'][0]['message']['tool_calls'][0]['function']['arguments']) #type: ignore
            for key, arg in args_dict.items():
                result += f'{key}: {arg.lower()}\n\n'
            return result.strip()
        else:
            args_dict = loads(json['choices'][0]['message']['content'])['parameters']                  #type: ignore
            for key, arg in args_dict.items():
                if isinstance(arg, str): result += f'{key}: {arg.lower()}\n\n'
                elif isinstance(arg, dict):
                    result += f'{key}:\n'
                    for inner_key, inner_arg in arg.items():
                        if isinstance(inner_arg, str)   : result += f'{inner_key}: {inner_arg.lower()}\n'
                        elif isinstance(inner_arg, list): result += f'{inner_key}: {"".join([a.lower() + ", " for a in inner_arg])}\n'   
                    result += '\n'  
                elif isinstance(arg, list):
                    #result += f'{key}: {"".join([a.lower() + ", " for a in arg if isinstance(arg, str)])}\n\n'     
                    result += f'{key}: {"".join([str(type(a)) + ", " for a in arg])}\n\n'       
            return result.strip()   
    except Exception as e:
        if _1st_try == True: return await EntityAnalysisOpenRouter(ent, cntx, kword, model, prompts, _1st_try=False)   
        #print(str(e))
        msg = f'Error calling OpenAI API: {e}'      
        return msg          

async def EntityAnalysis(ent, cntx, kword):
    return await EntityAnalysisF(ent, cntx, kword)
    prompt  = PROMPT.ENTITY_ANALISYS_PROMPT.format(ent, cntx, kword)
    return await ACompletion(prompt, temp=0.2, top_p=0.7)                  

async def GenerateAnchors(entity, kword, exclusions = []):
    try:
        prompt     = PROMPT.GEN_ANCHORS
        to_replace = 'Ensure that each generation is different from the others.' 
        if len(exclusions) > 0:            
            exclusions_text = ''.join([exclusion + ', ' for exclusion in exclusions]).strip(' ').strip(',')
            replace_with    = f'''Ensure that each generation is different from the others and also different from the following anchors: {exclusions_text}'''
            prompt          = prompt.replace(to_replace, replace_with)
        
        prompt   = prompt.format(kword, entity, kword, kword)
        messages = [{'role': 'user', 'content': prompt}]
        response = await ChatCompletion.acreate(
            model='gpt-4', temperature=0.2, messages=messages,            
            tools = [
                {
                    'type': 'function',
                    'function': {
                        'name': 'enum_anchors', 
                        'description' : 'enumerate generated anchors',                  
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'anchor1': {
                                    'type': 'string',                                
                                },  
                                'anchor2': {
                                    'type': 'string',                                
                                }, 
                                'anchor3': {
                                    'type': 'string',                                
                                }, 
                                'anchor4': {
                                    'type': 'string',                                
                                }, 
                                'anchor5': {
                                    'type': 'string',                                
                                },                                                      
                            },
                            'required': ['anchor1', 'anchor2', 'anchor3', 'anchor4', 'anchor5'],
                        },
                    },
                }
            ]
        )
        args_dict = loads(response['choices'][0]['message']['tool_calls'][0]['function']['arguments']) #type: ignore
        args      = [args_dict[key] for key in args_dict.keys()]
        return args
    except Exception as e:
        print(str(e))
        msg = f'Error calling OpenAI API: {e}'      
        return [msg, msg, msg, msg, msg]         


async def GenerateAnchorsOpenRouter(entity, kword, model, exclusions = []):
    try:
        prompt     = PROMPT.GEN_ANCHORS
        to_replace = 'Ensure that each generation is different from the others.' 
        if len(exclusions) > 0:            
            exclusions_text = ''.join([exclusion + ', ' for exclusion in exclusions]).strip(' ').strip(',')
            replace_with    = f'''Ensure that each generation is different from the others and also different from the following anchors: {exclusions_text}'''
            prompt          = prompt.replace(to_replace, replace_with)
        
        prompt   = prompt.format(kword, entity, kword, kword)
        messages = [{'role': 'user', 'content': prompt}]
        json = {
                'model'       : model,
                'messages'    : messages,  
                'temperature' : 0.2,              
                'tools' : [
                    {
                        'type': 'function',
                        'function': {
                            'name': 'enum_anchors', 
                            'description' : 'enumerate generated anchors',                  
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'anchor1': {
                                        'type': 'string',                                
                                    },  
                                    'anchor2': {
                                        'type': 'string',                                
                                    }, 
                                    'anchor3': {
                                        'type': 'string',                                
                                    }, 
                                    'anchor4': {
                                        'type': 'string',                                
                                    }, 
                                    'anchor5': {
                                        'type': 'string',                                
                                    },                                                      
                                },
                                'required': ['anchor1', 'anchor2', 'anchor3', 'anchor4', 'anchor5'],
                            },
                        },
                    }
                ]
            }

        async with ClientSession() as session:
            async with session.post('https://openrouter.ai/api/v1/chat/completions',
                    headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                    json = json
                    ) as response:
                if response.status == 200: 
                    json = await response.json() 
                elif response.status == 429:   
                    await async_sleep(1.1)
                    return await GenerateAnchorsOpenRouter(entity, kword, model, exclusions)                          
                else:                                
                    return f'Error calling Open Router API: Response.status == {response.status} calling Open Router API'    
       
        print(dumps(json, indent=4))
        if model.startswith('openai/'):
            args_dict = loads(json['choices'][0]['message']['tool_calls'][0]['function']['arguments']) #type: ignore
            args      = [args_dict[key] for key in args_dict.keys()]
            return args
        else:
            content   = loads(json['choices'][0]['message']['content'])
            args_dict = content['parameters'] if 'parameters' in content.keys() else content['enum_anchors']   
            args      = [args_dict[key] for key in args_dict.keys()]
            return args    
    except Exception as e:
        print(str(e))
        msg = f'Error calling Open Router API: {e}'      
        return [msg, msg, msg, msg, msg]         
