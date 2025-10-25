import json
from logging import PlaceHolder
from dashboard.app import g_, Pooled, Pool, IsDebugEnabled, GetCurrentUserid, flask_templace
from flask import jsonify
from asyncio import sleep as async_sleep
from dashboard.constants import STATUS, PROMPT
from flask import request
from dashboard.ChatGpt import OpenRouterAChat
from asyncio import create_task
from asyncio import gather
from dashboard.topic_cluster_creator import GenerateEntities, EntityAnalysisOpenRouter
from dashboard.content_creator import RemoveBadWordsB, FixTagCount, UpdateBlackLists, HightlightImportantTerms
from re import sub
from json import loads, dumps
from dashboard.alchemy import AlchemySetings, AlchemyLogs

def RemoveTaggedSectionNumbers(string):
    pattern = r'\s+[0-9.]+\s'   
    return sub(pattern, ' ', string)   

def GetMakrDownLevel(header):
    tag = header.strip().split(' ')[0]
    for char in tag: 
        if char != '#': return 0
    return tag.count('#')

def GetMarkDownArticleSections(article):
    sections   = ['']
    last_level = 0
    for line in article.splitlines():        
        level = GetMakrDownLevel(line)
        if level > 0:
            if level <= last_level: sections.append(line + '\n')
            else: sections[-1] += line + '\n'
            last_level = level
        else: sections[-1] += line + '\n'
    return sections                    

class GuesPost(Pooled):
    def __init__(self):
        super().__init__('GuestPost', 
        ['Generating Searcher Considerations', 'Generating Outline', 'Generating Article', 'Removing Black Listed Keywords', 'Generating Title Suggestions'])
        self.__pocoto               = 'pocoto'   
        self.__considerations       = ''     
        self.__FinalArticle         = '' 
        self.__Outline       :  str = ''
        self.__InitialArticle:  str = '' 
        self.__titles               = ''    
        self.__Analisys             = ''    
    
    def Finish(self, err: str) -> None:
        pass
        #self.__FinalArticle = 'PlaceHolder' 

    async def GenOutline(self, json: dict):
        print(self.__considerations)
        if self.__considerations.startswith('Error'): 
            self.__Outline = self.__considerations
            return
            
        #sys  = PROMPT.GUEST_POST_OUTLINE_SYSTEM.format(json['ArticleTitle'], json['Audience'], json['Tones'][0])
        #user = PROMPT.GUEST_POST_OUTLINE_USER.format(json['ArticleTitle'], 
        #self.__considerations, json['SpecialInstructions']['Outline'])

        tags = {'{TOPIC}' : 'ArticleTitle', '{AUDIENCE}' : 'Audience', '{TITLE}' : 'ArticleTitle', '{DATE}' : 'Today'}
        sys  = json['GuestPostingPrompts']['Outline System']   #type: ignore
        user = json['GuestPostingPrompts']['Outline User']     #type: ignore
        for tag, key in tags.items():                          #type: ignore
            sys  = sys.replace(tag, json[key])                 #type: ignore  
            user = user.replace(tag, json[key])                #type: ignore  

        sys  = sys.replace('{TONES}', json['Tones'])                                #type: ignore
        user = user.replace('{TONES}', json['Tones'])                               #type: ignore      
        sys  = sys.replace('{INSTRUCTIONS}', json['SpecialInstructions']['Outline'])  #type: ignore
        user = user.replace('{INSTRUCTIONS}',json['SpecialInstructions']['Outline'])  #type: ignore      
        sys  = sys.replace('{CONSIDERATIONS}', self.__considerations)                 #type: ignore
        user = user.replace('{CONSIDERATIONS}', self.__considerations)                #type: ignore 
        sys  = sys.replace('{SEMANTIC_ANALYSIS}', self.__Analisys)      #type: ignore
        user = user.replace('{SEMANTIC_ANALYSIS}', self.__Analisys)     #type: ignore

        if self.IsDebugEnabled(): return sys + user
        msgs   = [
            {'role' : 'system', 'content' : sys},
            {'role' : 'user', 'content'   : user}   
        ]        
        self.__Outline = await OpenRouterAChat(msgs, model=json['Models']['Outline'], temp=0.1) 
        #print(self.__Outline)
        if self.__Outline.find('Introduction') > -1: self.__Outline = 'Introduction' + self.__Outline.split('Introduction')[1]
        if self.__Outline.startswith('Error'): 
            self.__Outline = f'Error generating outline: {self.__Outline}'
            return       

    async def GenSearcherConsiderations(self, json: dict):
        if self.IsDebugEnabled(): 
            self.__considerations = 'PlaceHolder considerations'
            return        
        entities = await GenerateEntities(json['ArticleTitle'], json['Models']['Entities'])        
        if entities['CoreEntity'].startswith('Exception'): 
            self.__considerations = f'Error generating entities: {entities}'           
            return        
        analisys = await EntityAnalysisOpenRouter(entities['CoreEntity'], entities['ContextualFrame'], json['ArticleTitle'], json['Models']['Entities'])  
        if analisys.startswith('Error'): 
            self.__considerations = f'Error performing entity analisys: {analisys}'
            return
        try: 
            self.__Analisys        = analisys
            self.__considerations = analisys.split('Searcher Considerations:')[1].split('Attributes:')[0].strip()
        except Exception as e: self.__considerations = f'Error generating searcher considerations: {e}'
    
    async def GenArticle(self, json: dict):
        if self.__Outline.startswith('Error'):
            self.__InitialArticle = self.__Outline
            return
        #sys  = PROMPT.GUEST_POST_ARTICLE_SYSTEM.format(json['Today'])   
        #user = PROMPT.GUEST_POST_ARTICLE_USER.format(json['ArticleTitle'], json['MetaDescription'], self.__considerations, 
        #json['SpecialInstructions']['Content'], json['Tones'][0], json['AnchorText'], json['TargetURL'], json['Audience'], self.__Outline)  

        tags = {'{TOPIC}' : 'ArticleTitle', '{AUDIENCE}' : 'Audience', '{TITLE}' : 'ArticleTitle', 
        '{META}' : 'MetaDescription', '{ANCHOR}' : 'AnchorText',
        '{URL}' : 'TargetURL', '{DATE}' : 'Today'}

        sys  = json['GuestPostingPrompts']['Article System']   #type: ignore
        user = json['GuestPostingPrompts']['Article User']     #type: ignore
        for tag, key in tags.items():                          #type: ignore
            sys  = sys.replace(tag, json[key])                 #type: ignore  
            user = user.replace(tag, json[key])                #type: ignore  

        sys  = sys.replace('{TONES}', json['Tones'])         #type: ignore
        user = user.replace('{TONES}', json['Tones'])        #type: ignore    
        sys  = sys.replace('{INSTRUCTIONS}', json['SpecialInstructions']['Content'])  #type: ignore
        user = user.replace('{INSTRUCTIONS}',json['SpecialInstructions']['Content'])  #type: ignore      
        sys  = sys.replace('{OUTLINE}', self.__Outline)                 #type: ignore
        user = user.replace('{OUTLINE}', self.__Outline)                #type: ignore 
        sys  = sys.replace('{SEMANTIC_ANALYSIS}', self.__Analisys)      #type: ignore
        user = user.replace('{SEMANTIC_ANALYSIS}', self.__Analisys)     #type: ignore

        if self.IsDebugEnabled(): return self.__Outline + sys + user
        msgs = [
            {'role' : 'system', 'content' : sys},
            {'role' : 'user', 'content'   : user}   
        ]
        self.__InitialArticle = await OpenRouterAChat(msgs, model=json['Models']['Outline'], temp=0.5) 
        #print(self.__InitialArticle)
        if self.__InitialArticle.startswith('Error'): 
            self.__InitialArticle = f'Error generating article: {self.__InitialArticle}'
            return

    async def FixArticle(self, json: dict):       
        if self.__InitialArticle.startswith('Error'):
            self.__FinalArticle = self.__InitialArticle
            return
        if self.IsDebugEnabled(): return 
        fix_request = {
            'Article'             : FixTagCount(self.__InitialArticle),
            'Tones'               : json['Tones'],
            'Model'               : json['Models']['Fix'],
            'Model2ndPass'        : json['Models']['Model2ndPass'],
            'SelfReferecing'      : json['Models']['SelfReferecing'],
            'BlackListExclusions' : json['BlackListExclusions']
        }       
        self.__FinalArticle, _ = await RemoveBadWordsB(fix_request, self.IsDebugEnabled(), json['Prompts'])        
        if json['Highlight'] == 'HIGHLIGHT':                                                                                                       #type: ignore        
            sections     = await gather(*[HightlightImportantTerms(json['Prompts'], s, json['HModel']) for s in GetMarkDownArticleSections(self.__FinalArticle)])  #type: ignore 
            self.__FinalArticle = ''.join(sections)             
        if self.__FinalArticle.startswith('Error'): 
            self.__FinalArticle = f'Error fixing article: {self.__FinalArticle}'
            return
        if self.__FinalArticle.find('Introduction') > -1: self.__FinalArticle = 'Introduction' + self.__FinalArticle.split('Introduction')[1]
        #self.__FinalArticle = RemoveTaggedSectionNumbers(self.__FinalArticle)

    async def GenerateTitleSuggestions(self, json: dict):
        self.__titles = 'Titles placeholder'    
        
    async def Start(self, json: dict)->None: 
        await self.Next(self.GenSearcherConsiderations(json))  # type: ignore   
        await self.Next(self.GenOutline(json))                 # type: ignore 
        await self.Next(self.GenArticle(json))                 # type: ignore   
        await self.Next(self.FixArticle(json))                 # type: ignore 
        await self.Next(self.GenerateTitleSuggestions(json))   # type: ignore 
        
@g_.app.route('/guest-post-create', methods=['POST'])  #type: ignore    
async def CreateGuestPost():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    post = GuesPost()    
    if post.GetStatus() == STATUS.NOT_POOLED: return jsonify({'Err' : STATUS.NOT_POOLED})
    post.Run(request.json)      #type: ignore  
    return jsonify({'Reply' : post.serialize()})     

@g_.app.route('/guest-post_create-title-and-meta', methods=['POST'])                  #type: ignore    
async def GuestPostCreateTitleAndMeta():
    if '' == GetCurrentUserid(): return await flask_templace('login')       
    prompts = request.json['Prompts']                                                 #type: ignore    
    print(request.args)
    if request.json['title'] == '':                                        #type: ignore
        SYSTEM = prompts['System']                                         #type: ignore
        USER   = prompts['User'].replace('{TOPIC}', request.json['topic']) #type: ignore    
        msgs = [
            {'role' : 'system', 'content' : SYSTEM},
            {'role' : 'user', 'content'   : USER}   
        ]
        return jsonify({'Reply' : await OpenRouterAChat(msgs, model='google/gemini-pro-1.5', temp=0.3)})

    SYSTEM = prompts['System - only meta']                                             #type: ignore
    USER   = prompts['User - only meta'].replace('{TITLE}', request.json['topic'])     #type: ignore    
    msgs   = [
        {'role' : 'system', 'content' : SYSTEM},
        {'role' : 'user', 'content'   : USER}   
    ]
    return jsonify({'Reply' : await OpenRouterAChat(msgs, model='google/gemini-pro-1.5', temp=0.3)})    


@g_.app.route('/guest-post_create-considerations', methods=['POST'])                     #type: ignore       
async def GuestPostCreateConsiderations():
    if '' == GetCurrentUserid(): return await flask_templace('login')       
    if IsDebugEnabled(): return jsonify({'Reply' : 'PlaceHolder considerations'})
    json = request.json            
    entities = await GenerateEntities(json['ArticleTitle'], json['Models']['Entities'])  #type: ignore         
    if entities['CoreEntity'].startswith('Exception'): return jsonify({'Reply' : f'Error generating entities: {entities}'})             
    analisys = await EntityAnalysisOpenRouter(entities['CoreEntity'], entities['ContextualFrame'], 
    json['ArticleTitle'], json['Models']['Entities'])                                    #type: ignore    
    if analisys.startswith('Error'): return jsonify({'Reply' : f'Error performing entity analisys: {analisys}'})
    #try: return jsonify({'Reply' : analisys.split('Searcher Considerations:')[1].split('Attributes:')[0].strip()})
    try: return jsonify({'Reply' : analisys})
    except Exception as e: return jsonify({'Reply' : f'Error generating searcher considerations: {e}'})

@g_.app.route('/guest-post_create-outline', methods=['POST'])                            #type: ignore    
async def GuestPostCreateOutline():
    if '' == GetCurrentUserid(): return await flask_templace('login')        
    json = request.json
    
    tags = {'{TOPIC}' : 'ArticleTitle', '{AUDIENCE}' : 'Audience', '{INSTRUCTIONS}' : 'SpecialInstructions', '{TITLE}' : 'ArticleTitle', 
    '{CONSIDERATIONS}' : 'Considerations', '{SEMANTIC_ANALYSIS}' : 'SemanticAnalysis', '{DATE}' : 'Today'}

    #sys  = PROMPT.GUEST_POST_OUTLINE_SYSTEM.format(json['ArticleTitle'], json['Audience'], json['Tones'][0]) #type: ignore  
    #user = PROMPT.GUEST_POST_OUTLINE_USER.format(json['ArticleTitle'], json['Considerations'], json['SpecialInstructions'])  

    sys  = json['GuestPostingPrompts']['Outline System']   #type: ignore
    user = json['GuestPostingPrompts']['Outline User']     #type: ignore
    for tag, key in tags.items():                          #type: ignore
        sys  = sys.replace(tag, json[key])                 #type: ignore  
        user = user.replace(tag, json[key])                #type: ignore  

    sys  = sys.replace('{TONES}', json['Tones'])         #type: ignore
    user = user.replace('{TONES}', json['Tones'])        #type: ignore                                          
                                       
    if IsDebugEnabled(): return jsonify({'Reply' :sys + user})
    msgs   = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]        
    outline = await OpenRouterAChat(msgs, model=json['Model'], temp=0.1)   #type: ignore  
    if outline.find('Introduction') > -1: outline = 'Introduction' + outline.split('Introduction')[1]
    return jsonify({'Reply' :outline})                                     #type: ignore  

@g_.app.route('/guest-post_create-article', methods=['POST'])  
async def GuestPostCreateArticle():
    if '' == GetCurrentUserid(): return await flask_templace('login')        
    json = request.json
    #sys  = PROMPT.GUEST_POST_ARTICLE_SYSTEM.format(json['Today'])                                                               #type: ignore   
    #user = PROMPT.GUEST_POST_ARTICLE_USER.format(json['ArticleTitle'], json['MetaDescription'], json['Considerations'],         #type: ignore  
    #json['SpecialInstructions'], json['Tones'][0], json['AnchorText'], json['TargetURL'], json['Audience'], json['Outline'])    #type: ignore  
    
    tags = {'{TOPIC}' : 'ArticleTitle', '{AUDIENCE}' : 'Audience', '{INSTRUCTIONS}' : 'SpecialInstructions', '{TITLE}' : 'ArticleTitle', 
    '{CONSIDERATIONS}' : 'Considerations', '{META}' : 'MetaDescription', '{ANCHOR}' : 'AnchorText',
    '{URL}' : 'TargetURL', '{OUTLINE}' : 'Outline', '{DATE}' : 'Today', '{SEMANTIC_ANALYSIS}' : 'SemanticAnalysis'}

    sys  = json['GuestPostingPrompts']['Article System']   #type: ignore
    user = json['GuestPostingPrompts']['Article User']     #type: ignore
    for tag, key in tags.items():                          #type: ignore
        #print(tag, key, json[key])
        sys  = sys.replace(tag, json[key])                 #type: ignore  
        user = user.replace(tag, json[key])                #type: ignore  

    sys  = sys.replace('{TONES}', json['Tones'])         #type: ignore
    user = user.replace('{TONES}', json['Tones'])        #type: ignore    

    if IsDebugEnabled(): return jsonify({'Reply' : 'Article' + sys + user})                                                     #type: ignore  
    msgs = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]
    article =  await OpenRouterAChat(msgs, model=json['Model'], temp=0.5)                                                       #type: ignore  
    fix_request = {
        'Article' : FixTagCount(article),                                                                                       #type: ignore  
        'Tones'   : json['Tones'],                                                                                              #type: ignore  
        'Model'   : json['FixModel'],                                                                                           #type: ignore  
        'Model2ndPass'   : json['Model2ndPass'],                                                                                #type: ignore  
        'SelfReferecing' : json['SelfReferecing'],                                                                              #type: ignore  
        'Tones'          : json['Tones'],                                                                                       #type: ignore  
        'Audience'       : json['Audience']                                                                                     #type: ignore  
    }
    if article.startswith('Error'): return jsonify({'Reply' : article})         
    FinalArticle, _ = await RemoveBadWordsB(fix_request, IsDebugEnabled(), json['Prompts'])                                     #type: ignore 
    if json['Highlight'] == 'HIGHLIGHT':                                                                                        #type: ignore        
        sections     = \
        await gather(*[HightlightImportantTerms(json['Prompts'], s, json['HModel']) for s in GetMarkDownArticleSections(FinalArticle)])                                                                            #type: ignore 
        FinalArticle = ''.join(sections)                                                                                        #type: ignore                         
    if FinalArticle.startswith('Error'): return jsonify({'Reply' : RemoveTaggedSectionNumbers(FixTagCount(article))})           #type: ignore
    if FinalArticle.find('Introduction') > -1: FinalArticle = 'Introduction' + FinalArticle.split('Introduction')[1]
    return jsonify({'Reply' : RemoveTaggedSectionNumbers(FinalArticle)})                                                        #type: ignore
    

@g_.app.route('/guest-post_set-default', methods=['POST'])                                                                      #type: ignore
async def GuestPostSetDefault(): 
    _id           = GetCurrentUserid()  
    loger         = AlchemyLogs()   
    key           = 'Guest Posting Default Instructions'
    whitch        = request.args.get('whitch')                                                                                  #type: ignore
    value         = request.json.get('value')                                                                                   #type: ignore   
    settings_wrap = AlchemySetings()

    settings      = settings_wrap.Get(g_.SharedDataID) 
    loger.log(_id, 'Current Settings:\n' + dumps(settings, indent=4))

    if key not in settings: 
        loger.log(_id, f'Key {key} not in settings, RESETING')
        settings[key] = {'Outline' : '', 'Article' : ''}
    else: 
        loger.log(_id, f'Updating {whitch} to {value}')
        settings[key][whitch] = value

    settings_wrap.Set(g_.SharedDataID, key, settings[key]) 
    new_val = settings_wrap.Get(g_.SharedDataID)
    loger.log(_id, 'Updated Settings:\n' + dumps(new_val, indent=4))

    return jsonify({'Reply': new_val[key]})



    key       = 'Guest Posting Default Instructions'
    whitch    = request.args.get('whitch')                                                                                      #type: ignore
    value     = request.json.get('value')                                                                                       #type: ignore
    setttings = g_.db.LoadCluster(g_.SharedDataID, request.args.get('SettingsID'))
    if setttings is None:             setttings = {}
    elif isinstance(setttings, str):  setttings = loads(setttings)
    
    if key not in setttings.keys():
        setttings[key] = {                                                                                                       #type: ignore 
            'Outline' : 'The outline should not contain the word "Understanding" or "Definition."',
            'Article' : 'The internal link should not placed in the introduction or conclusion. Use the most relevant section to insert the link.'
        }
    
    if whitch is not None and value is not None:
        setttings[key][whitch] = value                                                                                           #type: ignore 
    
    g_.db.WriteCluster(g_.SharedDataID, request.args.get('SettingsID'), dumps(setttings))                                      
    return jsonify({'Reply' : setttings})


@g_.app.route('/guest-post_get-defaults', methods=['POST'])
async def GuestPostGetDefaults():
    _id           = GetCurrentUserid()  
    loger         = AlchemyLogs()       
    key           = 'Guest Posting Default Instructions'
    settings_wrap = AlchemySetings()

    settings      = settings_wrap.Get(g_.SharedDataID)
    loger.log(_id, 'Current Settings:\n' + dumps(settings, indent=4)) 

    if key not in settings: 
        loger.log(_id, f'Key {key} not in settings, RESETING')
        settings_wrap.Set(g_.SharedDataID, key, {'Outline' : '', 'Article' : ''}) 

    return jsonify({'Reply': settings_wrap.Get(g_.SharedDataID)[key]})


    key         = 'Guest Posting Default Instructions'
    settings_id = request.args.get('SettingsID')
    setttings   = g_.db.LoadCluster(g_.SharedDataID, settings_id)
    if setttings is None:            setttings = {}
    elif isinstance(setttings, str): setttings = loads(setttings)

    if key not in setttings:                                 
        setttings[key] = {                                                                                                       #type: ignore 
            'Outline': 'The outline should not contain the word "Understanding" or "Definition."',
            'Article': 'The internal link should not placed in the introduction or conclusion. Use the most relevant section to insert the link.'
        }

    if 'Outline' not in setttings[key]:
        setttings[key]['Outline'] = 'The outline should not contain the word "Understanding" or "Definition."'                   #type: ignore 

    if 'Article' not in setttings[key]:                                                                                          
        setttings[key]['Article'] = 'The internal link should not placed in the introduction or conclusion. Use the most relevant section to insert the link.' #type: ignore 

    return jsonify({'Reply': setttings[key]})
