from json import loads
from logging import PlaceHolder, debug
from math import e
from re import sub, match
from dashboard.constants import PROMPT, STATUS
from dashboard.ChatGpt import AChat, OpenRouterAChat
from dashboard.app import g_, IsDebugEnabled, GetCurrentUserid, flask_templace, IsAdmin, err, Pooled
from flask import jsonify, request
from asyncio import gather
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import download, ngrams, data as nltk_data
from copy import deepcopy
from pathlib import Path
from tempfile import gettempdir
nltk_data.path.append(gettempdir())
download('punkt', download_dir=gettempdir())
from json import loads, dumps
from string import punctuation
from dashboard.alchemy import AlchemyLogs, postlog, AlchemyBlackLists

from os.path import dirname, realpath 
with open(dirname(realpath(__file__)) + '/resources/blacklisted_words.txt', 'r', encoding="cp1252") as f: 
    g_.BlackList['Articles']  = [word.strip('\n').strip('\r').strip('\n').strip(' ') for word in f.read().splitlines()]
    g_.BlackList['Outlines']  = []

def RemoveXMLTags(reply): 
    orig = deepcopy(reply)  
    try: reply = reply.split('<new>')[1].split('</new>')[0]
    except(IndexError): reply = reply    
    try: reply = reply.split('<content>')[1].split('</content>')[0]
    except(IndexError): reply = reply    
    return reply 
    return orig + '<===>' + reply  

@g_.app.route("/content_creator-get_blacklisted_words", methods=['POST'])               #type: ignore 
async def content_creator_get_blacklisted_words():      
    which             = request.args.get('list')
    #json              = loads(g_.db.LoadCluster(g_.SharedDataID, g_.SharedBlackListID)) #type: ignore    
    json              = AlchemyBlackLists().GetAll()
    if not 'Self References Black List' in json.keys(): json['Self References Black List'] = []
    if not 'Stop Words'                 in json.keys(): json['Stop Words']                 = []
    g_.BlackList['Articles']         = json[f'Articles Black List']                       
    g_.BlackList['Outlines']         = json[f'Outlines Black List']  
    g_.BlackList['Self References']  = json[f'Self References Black List']     
    g_.BlackList['Stop Words']       = json[f'Stop Words']           
    return jsonify({'Reply' : json[f'{which}']}) if which == 'Stop Words' else jsonify({'Reply' : json[f'{which} Black List']})       

def UpdateBlackLists():
    #json   = loads(g_.db.LoadCluster(g_.SharedDataID, g_.SharedBlackListID)) #type: ignore    
    json              = AlchemyBlackLists().GetAll()
    if not 'Self References Black List' in json.keys(): json['Self References Black List'] = []
    g_.BlackList['Articles']         = json[f'Articles Black List']         
    g_.BlackList['Outlines']         = json[f'Outlines Black List']         
    g_.BlackList['Self References']  = [word.strip().lower() for word in json[f'Self References Black List']]
    #g_.BlackList['Stop Words']       = json[f'Stop Words']   

@g_.app.route("/content_creator-set_blacklisted_words", methods=['POST'])     #type: ignore   
async def content_creator_set_blacklisted_words():    
    if False == IsAdmin(): return err('Not admin')
    which                         = request.args.get('list')
    _words                        = loads(g_.db.LoadCluster(g_.SharedDataID, g_.SharedBlackListID)) #type: ignore 
    if not 'Self References Black List' in _words.keys(): _words['Self References Black List'] = []
    if not 'Stop Words'                 in _words.keys(): _words['Stop Words']                 = []
    if which == 'Stop Words': _words[f'Stop Words']            = request.json['Black List']         #type: ignore
    else                    : _words[f'{which} Black List']    = request.json['Black List']         #type: ignore 
    g_.BlackList['Articles']          = [word.strip() for word in _words[f'Articles Black List']]
    g_.BlackList['Outlines']          = [word.strip() for word in _words[f'Outlines Black List']]    
    g_.BlackList['Self References']   = [word.strip() for word in _words[f'Self References Black List']]    
    g_.BlackList['Stop Words']        = [word.strip() for word in _words[f'Stop Words']]     
    #g_.db.WriteCluster(g_.SharedDataID, g_.SharedBlackListID, dumps(_words))
    AlchemyBlackLists().SetAll(_words)
    return jsonify({'' : g_.BlackList['Articles']})

def SplitSetence(setence):
    if setence.startswith('#'):
        split = setence.split(' ')
        if len(split) >= 2:                
            if split[0] == ''.join(['#' for char in split[0]]):                
                prefix = split[0] + ' '
                return setence.replace(split[0] + ' ', '', 1), prefix
    return setence, ''

async def RemoveTermsFromSentence(msgs, model, temp):
    reply      = await OpenRouterAChat(msgs, model=model, temp=0.5)  
    found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
    count      = 0
    while reply.startswith('Error calling Open Router API: ') or not found_tags:
        reply      = await OpenRouterAChat(msgs, model=model, temp=0.5)  
        found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
        count     += 1
        if count  == 4: break
    
    return RemoveXMLTags(reply)   

async def RemoveSelfReferences(sentence, rqst, dbug, prompts:None|dict=None)->str:    
    if 'Ignore Self Rererences' in rqst.keys() and rqst['Ignore Self Rererences'] == 'Ignore': return sentence
    black_list = [word for word in NGramsTokenizer(sentence.lower(), 5) if word in g_.BlackList['Self References']]
    if len(black_list) == 0: return sentence
    bad      = ''.join([black + ', ' for black in black_list]).strip(',')
    if prompts == None: 
        sys    = PROMPT.SELF_REFERENCING_SYSTEM.format(rqst['Audience'], rqst['Tones'][0])
        user   = PROMPT.SELF_REFERENCING_USER.format(sentence)
    else:
        sys    = prompts['Self referencing - System'].replace('{REMOVALS}', bad).replace('{CONTENT}', sentence)                  #type: ignore
        user   = prompts['Self referencing - User'].replace('{REMOVALS}', bad).replace('{CONTENT}', sentence) 

    msgs   = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]    
    if dbug: return 'Self References removed: ' + sentence
        
    reply      =  await RemoveTermsFromSentence(msgs, model=rqst['SelfReferecing'], temp=0.5)     
    return RemoveXMLTags(reply)  

def RemoveExtraLineFeeds(orignal, fixed):
    if not orignal.endswith('\n'): fixed = fixed.rstrip('\n')
    if not fixed.endswith('\n'):   fixed = fixed.lstrip('\n')
    return fixed

def ProcessAIWordsPrompt(prompt, bad_words, bad_words_full, sentence):   
    return prompt.replace('{REMOVALS}', bad_words).replace('{CONTENT}', sentence['Sentence']).replace(
    '{FULL_PROHIBITED_WORDS_LIST}', bad_words_full).replace('{PREV_SENTENCE}', sentence['Prev']).replace('{NEXT_SENTENCE}', sentence['Next'])

async def RemoveBlackListedKeywords(sentence, black_list, rqst, dbug, prompts:None|dict=None):
    if len(black_list) == 0: return await RemoveSelfReferences(sentence['Sentence'], rqst, dbug)
    
    full_bad_words_list = ''.join([black + ', ' for black in black_list]).strip(',')
    sequence         = sentence
    sentence, prefix = SplitSetence(sentence['Sentence'])
    sentence = await RemoveSelfReferences(sentence, rqst, dbug, prompts) #type: ignore
    bad      = ''.join([black + ', ' for black in black_list]).strip(',')
    if prompts == None: 
        sys    = PROMPT.CONTENT_CLEANUP_SYSTEM.format(bad, rqst['Tones'])
        user   = PROMPT.CONTENT_CLEANUP_USER.format(bad, sentence)
    else:
        #sys    = prompts['AI Words - System'].replace('{REMOVALS}', bad).replace('{CONTENT}', sentence)   #type: ignore
        #user   = prompts['AI Words - User'].replace('{REMOVALS}', bad).replace('{CONTENT}', sentence)    #type: ignore
        sys     = ProcessAIWordsPrompt(prompts['AI Words - System'], bad, full_bad_words_list, sequence)   #type: ignore
        user    = ProcessAIWordsPrompt(prompts['AI Words - User'], bad, full_bad_words_list, sequence)    #type: ignore
 
    msgs   = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]    
    if dbug: return 'Fixed ' + prefix + sentence    
   
    _1st_pass = await RemoveTermsFromSentence(msgs, model=rqst['Model'], temp=0.5)  

    found = False
    for black in black_list:
        if black in _1st_pass: found = True
    if found == False: return prefix + _1st_pass

    sentence, prefix =  SplitSetence(prefix + _1st_pass)
    bad    = ''.join([black + ', ' for black in black_list]).strip(',')
    sys    = PROMPT.CONTENT_CLEANUP_SYSTEM.format(bad, rqst['Tones'])
    user   = PROMPT.CONTENT_CLEANUP_USER.format(bad, sentence)
    msgs   = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]
    
    _2nd_pass = await RemoveTermsFromSentence(msgs, model=rqst['Model2ndPass'], temp=0.5)       
    return prefix + _2nd_pass

def Tuple2Gram(gram):
   return ''.join([g.strip('\n').strip('\n') + ' ' for g in gram]).strip()

def NgramTokenizer(setence, n):
    return [Tuple2Gram(gram) for gram in ngrams(setence.split(' '), n)]

def NGramsTokenizer(setence, max):
    exclude = list(punctuation)
    #print(exclude)
    exclude.append('\n')
    exclude.pop(exclude.index("'")) 
    #print(exclude)
    setence = ''.join(ch for ch in setence if ch not in exclude).strip("´")
    grams = word_tokenize(setence)
    for n in range(2, max+1):
        grams.extend(NgramTokenizer(setence, n))            
    return grams     

def GetBlackListedWordsInSetence(setence, excusions = []):
    if setence.strip().startswith("#"): return []
    #words     = word_tokenize(setence.lower())
    words     = NGramsTokenizer(setence.lower(), 5)    
    bad_words = [word for word in g_.BlackList['Articles'] if word.strip().lower() in words and word.strip().lower() not in excusions]
   
    return bad_words

def ArticleSetenceTokenizer(article):
    #article = article.replace('\n', ' \n ')
    final   = []
    for s in article.split('\n'):        
        if s.strip() == '': continue
        final.extend(sent_tokenize(s))
    #print(final)
    return final
    return [s.replace('\n', ' \n') for s in sent_tokenize(article)]

def GetSentenceSequence(index, sentences):
    sentence = sentences[index]
    prev     = sentences[index - 1] if index > 0 else ''
    nxt      = sentences[index + 1] if index < len(sentences) - 1 else ''
    return {'Sentence' : sentence, 'Prev' : prev, 'Next' : nxt}    
                  
@g_.app.route("/content_creator-remove_blacklisted_words", methods=['POST'])  #type: ignore 
async def RemoveBadWords():
    #print(IsDebugEnabled())
    if ''    == GetCurrentUserid(): return await flask_templace('login')     
    rqst      = request.json   
    sentences = sent_tokenize(rqst['Section'])                                #type: ignore      
    bad       = [GetBlackListedWordsInSetence(setence) for setence in sentences]    
    fixed     = await gather(*[RemoveBlackListedKeywords(GetSentenceSequence(index, sentences), black_list, rqst, IsDebugEnabled()) 
    for index, black_list in enumerate(sentences, bad)])                      #type: ignore    
    section   = rqst['Section']                                               #type: ignore    
    for original, fix in zip(sentences, fixed): section = section.replace(original, fix)
    summary   = []
    for orig, fix, removals in zip(sentences, fixed, bad):
        if len(removals) > 0:
            summary.append({'Original' : orig, 'Fixed' : fix, 'Removals' : removals})
    if IsDebugEnabled():        
        return jsonify({'Reply' : 'FIXED PLACEHOLDER FOR: ' + section, 'Summary' : summary})
    return jsonify({'Reply' : section, 'Summary' : summary})

def RemoveTagsB(msg):
    return sub(r'#\s[0-9.]+\s', '# ', msg, 0) 

def IsMarkdownSectionNumber(text):
    for char in text.strip():
        if not (char == '#' or char == '.' or char.isnumeric() or char == ' '): return False
    return True        

def TokenizeArticle(article):
    nltk_tokens = ArticleSetenceTokenizer(article)
    if len(nltk_tokens) == 0: return []
    tokens = [nltk_tokens[0]]
    for token in nltk_tokens[1::]:
        if IsMarkdownSectionNumber(tokens[-1]): tokens[-1] += ' ' + token
        else: tokens.append(token)
    return tokens           

#@g_.app.route("/content_creator-remove_blacklisted_words", methods=['POST'])              #type: ignore 
async def RemoveBadWordsB(rqst, debug, prompts=None, exclusions=''):    
    #if ''               == GetCurrentUserid(): return await flask_templace('login')    
    exc                  = [ex.strip().lower() for ex in exclusions.splitlines()]
    sentences            = TokenizeArticle(rqst['Article'])                                #type: ignore      
    bad                  = [GetBlackListedWordsInSetence(setence, exc) for setence in sentences]    
    fixed                = await gather(*[RemoveBlackListedKeywords(GetSentenceSequence(index, sentences), black_list, rqst, debug, prompts) 
    for index, black_list in enumerate(bad)])   
    bad2nd               = [GetBlackListedWordsInSetence(setence, exc) for setence in fixed]    
    for index, bad2 in enumerate(bad2nd): bad2nd[index].extend(bad[index])
    fixed2nd             = await gather(*[RemoveBlackListedKeywords(GetSentenceSequence(index, fixed), black_list, rqst, debug, prompts) 
    for index, black_list in enumerate(bad2nd)])
    section              = rqst['Article']                                                 #type: ignore    
    LinefeedsFixed       = [RemoveExtraLineFeeds(original, fix) for original, fix in zip(sentences, fixed2nd)]
    for original, fix in zip(sentences, LinefeedsFixed): section = section.replace(original.strip('\n'), fix.strip('\n'))    
    if debug:  return 'FIXED PLACEHOLDER FOR: ' + section, bad
    return section, bad

@g_.app.route("/content_creator-remove_blacklisted_words_b", methods=['POST'])  #type: ignore
async def RemoveBadWordsBRoute():
    if ''           == GetCurrentUserid(): return await flask_templace('login')
    if request.json ==  None             : return err('No data')
    UpdateBlackLists()
    rqst            = request.json
    debug           = IsDebugEnabled()
    prompts         = rqst['Prompts']
    exclusions      = rqst['BlackListExclusions'] 
    section, bad    = await RemoveBadWordsB(rqst, debug, prompts, exclusions)
    return jsonify({'Reply' : section, 'Removals' : bad})

def IsTagOnly(text):
    for char in text:
        if char != '#': return False 
    return True  

def MakeTags(count):
    return ''.join(['#' for i in range(count)])  

def IsSectionNumberStrict(text):
    for char in text:
        if not (char == '.' or char.isnumeric()): return False
    return True

def FixTagCount(text):
    new_text = ''
    for line in text.splitlines():
        split = line.strip().split(' ') 
        if len(split) > 1 and IsTagOnly(split[0]) and IsSectionNumberStrict(split[1]):
            new_text += MakeTags(split[1].count('.') + 1) + ' ' + ' '.join(split[1::]) + '\n'
        else: new_text += line + '\n'    
    return new_text

async def HightlightImportantTerms(prompts, section, model):   
    msgs = [
        {'role' : 'system', 'content' : prompts['Bold words - System'].replace('{CONTENT}', section)}, #type: ignore
        {'role' : 'user', 'content'   : prompts['Bold words - User'].replace('{CONTENT}', section)}    #type: ignore
    ]

    reply      = 'Error calling Open Router API: '
    found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
    count      = 0
    while reply.startswith('Error calling Open Router API: ') or not found_tags:
        reply      = await OpenRouterAChat(msgs, model=model, temp=0.2)  
        found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
        count     += 1
        if count  == 4: break

    return RemoveXMLTags(reply)  

async def ImproveWithLinksCountCheck(messages, model, temp):
    reply         = await OpenRouterAChat(messages, model=model, temp=temp)
    user          = messages[-1]['content']
    return reply
    if reply.startswith('Error calling Open Router API: '): return reply # let the caller handle it
    missing_links = GetMissingLinksCount(user, reply)
    if missing_links == 0: return reply
    if missing_links > 0: 
        new_reply             = await OpenRouterAChat(messages, model=model, temp=temp)
        missing_links_2nd_try = GetMissingLinksCount(user, new_reply)
        return new_reply if missing_links_2nd_try < missing_links else reply
    return reply        

async def ImproveArticleB(msgs, model, temp=0.5):    
    #reply      = await OpenRouterAChat(msgs, model=model, temp=0.5)  
    reply      = await ImproveWithLinksCountCheck(msgs, model, temp)  
    found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
    count      = 0
    while reply.startswith('Error calling Open Router API: ') or not found_tags:
        #reply      = await OpenRouterAChat(msgs, model=model, temp=0.5)  
        reply      = await ImproveWithLinksCountCheck(msgs, model, temp)  
        found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
        count     += 1
        if count  == 4: break

    return RemoveXMLTags(reply)  

async def InsertLinks(section, json):
    if json['Links'] == '' or 'System' not in json['Links Prompts'] or 'User' not in json['Links Prompts']: return section
    user   = json['Links Prompts']['User'].replace('{CONTENT}', section).replace('{INTERNAL_LINKS}', json['Links'])
    system = json['Links Prompts']['System'].replace('{CONTENT}', section).replace('{INTERNAL_LINKS}', json['Links'])
    msgs   = [
        {
            'role'    : 'system', 
            'content' : system
        }, 
        {
            'role'     : 'user', 
            'content'  : user
        }    
    ]
    reply = await OpenRouterAChat(msgs, model=json['Links Model'])  
    count = 0
    while reply.startswith('Error calling Open Router API: ') or GetMissingLinksCount(user, reply)  or GetMissingLinksCount(system, reply)> 0:        
        reply      = await OpenRouterAChat(msgs, model=json['Links Model'], temp=0.3)          
        count     += 1
        if count  == 4: break

    return RemoveXMLTags(reply)  

async def ImproveAndFix(rqst, prompts=None, choices=None):  
    #print(dumps(request.json, indent=4))                                    #type: ignore   
    sys             = rqst['System']                                         #type: ignore   
    user            = rqst['User']                                           #type: ignore        
    model           = rqst['Model']                                          #type: ignore   
    do_improve      = True
    do_highlight    = False
    if choices is not None:
        do_improve   = False if choices['Improve']   == '' else True    #type: ignore     
        do_highlight = False if choices['Highlight'] == '' else True     
    __rqst          = deepcopy(rqst)                      
    orginal         =  __rqst['Article']                                     #type: ignore 
    __rqst['Model'] =  __rqst['IModel']                                      #type: ignore 
    user = user.replace(rqst['Article'], FixTagCount(rqst['Article']))       #type: ignore
    temp = rqst['temp'] if 'temp' in rqst  else 0.5 
    if IsDebugEnabled() == False:     
        msgs = [
            {'role' : 'system', 'content' : sys},
            {'role' : 'user', 'content'   : user}   
        ]
        if do_improve: __rqst['Article'] = await ImproveArticleB(msgs, model=model, temp=temp)  #type: ignore 
        else:
            print('Skipping improve') 
            __rqst['Article'] = orginal.replace(rqst['Article'], FixTagCount(rqst['Article']))         
    
    exclusions = rqst['BlackListExclusions'] if 'BlackListExclusions' in rqst.keys() else ''
    fixed, bad = await RemoveBadWordsB(__rqst, IsDebugEnabled(), prompts, exclusions)
    _bad = []
    for b in bad: _bad.extend(b)
    fixed = await InsertLinks(fixed, __rqst)
    if do_highlight: fixed = await HightlightImportantTerms(prompts, fixed, rqst['HModel'])
    return {'Reply' : RemoveTagsB(fixed), 'System' : sys, 'User' : user, 'Removals' : _bad, 'Improved' : __rqst['Article'], 'Original' : orginal}
   
@g_.app.route('/content_creator-improve_and_fix', methods=['POST']) 
async def ImproveAndFixOne(): 
    UpdateBlackLists()
    return jsonify(await ImproveAndFix(request.json))

@g_.app.route('/content_creator-improve_and_fix_all', methods=['POST'])                    #type: ignore 
async def ImproveAndFixAll(): 
    UpdateBlackLists()
    requests = request.json['Requests']                                                    #type: ignore   
    Prompts  = request.json['Prompts']                                                     #type: ignore      
    choices  = request.json['Choices'] if 'Choices' in request.json.keys() else None       #type: ignore 
    replies  = await gather(*[ImproveAndFix(rqst['Data'], Prompts, choices) for rqst in requests])  #type: ignore 
    return jsonify({'Replies' : replies})

def SplitOutlineSetence(setence): pass

@g_.app.route('/content_creator-gen-section-facts', methods=['POST'])                       #type: ignore 
async def GenSectionFacts():    

    def ProcessSectionFacst(facts):
        try:
            return facts.split('<facts>')[1].split('</facts>')[0]
        except(IndexError):
            return facts    

    if '' == GetCurrentUserid(): return await flask_templace('login')
    json  = request.json 
    if json == None: return jsonify({'Err' : 'Error generating section facts, No data'})
    if 'Model' not in json.keys() or 'Section' not in json.keys() or 'Keyword' not in json.keys() \
        or 'Sys' not in json.keys() or 'User' not in json.keys(): 
        return jsonify({'Err' : 'Error generating section facts, No model, section or keyword'})
    model   = json['Model']    
    section = json['Section']
    keyword = json['Keyword']      
    sys     = json['Sys'].replace('{SECTION}', section).replace('{KEYWORD}', keyword)
    user    = json['User'].replace('{SECTION}', section).replace('{KEYWORD}', keyword)
    msgs    = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user'  , 'content'   : user}
    ]                          
    reply = await OpenRouterAChat(msgs, model=model, temp=0.5)
    reply = sub(r'\[.*?\]', '', reply)       
    reply = ProcessSectionFacst(reply)
    return jsonify({'Err' : 'S_OK',  'Reply' : reply, 'System' : sys, 'User' : user})        

async def RemoveOutlineBlackListedKeywords(sentence, black_list, rqst):   
    if len(black_list) == 0: return 'Nothing to fix on: ' + sentence if IsDebugEnabled() == True else sentence    
    
    sentence, prefix =  SplitSetence(sentence)
    bad    = ''.join([black + ', ' for black in black_list]).strip(',')
    sys    = PROMPT.OUTLINE_BLACKLIST_SYSTEM.format(bad)
    user   = PROMPT.OUTLINE_BLACKLIST_USER.format(sentence)
    msgs   = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]    
    
    count = 0
    _1st_pass = 'Error calling Open Router API: '
    while _1st_pass.startswith('Error calling Open Router API: ') and count < 3:        
        _1st_pass = await OpenRouterAChat(msgs, model=rqst['Model'], temp=0.5)
        _1st_pass = RemoveXMLTags(_1st_pass)          
        count += 1  
    if _1st_pass.startswith('Error calling Open Router API: '): return prefix + _1st_pass      

    _1st_tokens = NGramsTokenizer(_1st_pass.lower(), 5)    
    found = False
    for black in black_list:
        if black in _1st_tokens: found = True
    if found == False: return prefix + _1st_pass

    sentence, prefix =  SplitSetence(prefix + _1st_pass)
    bad    = ''.join([black + ', ' for black in black_list]).strip(',')
    sys    = PROMPT.OUTLINE_BLACKLIST_SYSTEM.format(bad, rqst['Tones'])
    user   = PROMPT.OUTLINE_BLACKLIST_USER.format(bad, sentence)
    msgs   = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]
    count = 0
    _2nd_pass = 'Error calling Open Router API: '
    while _2nd_pass.startswith('Error calling Open Router API: ') and count < 3:        
        _2nd_pass = await OpenRouterAChat(msgs, model=rqst['Model2ndPass'], temp=0.5)
        _2nd_pass = RemoveXMLTags(_2nd_pass)         
        count += 1   
    if _2nd_pass.startswith('Error calling Open Router API: '): return prefix + _1st_pass          
        
    return prefix + _2nd_pass  

def GetBlackListedWordsInSetenceB(setence, bad_words):
    if setence.strip().lower().startswith('- brief'): 
        return []
    words     = word_tokenize(setence.lower(), language='english')
    bad_words = [word for word in bad_words if word.lower() in words]
    return bad_words

def TokenizeOutline(outline):    
    tokens = []
    for token in outline.split('\n'):
        if token != '': tokens.append(token)
    return tokens        

async def __RemoveBadWordsFromOutline(rqst):      
    if ''               == GetCurrentUserid(): return await flask_templace('login')    
    sentences            = TokenizeOutline(rqst['Outline'])                              #type: ignore      
    bad                  = [GetBlackListedWordsInSetenceB(setence, g_.BlackList['Outlines']) for setence in sentences]    
    fixed                = await gather(*[RemoveOutlineBlackListedKeywords(sentence, black_list, rqst) for sentence, black_list in zip(sentences, bad)])  
        
    section              = rqst['Outline']                                               #type: ignore  
    replacements         = []
    for og, fix in zip(sentences, fixed):
        if og == fix: continue
        replacements.append({'Og' : og, 'Fix' : fix})
    for original, fix in zip(sentences, fixed): section = section.replace(original, fix)   
    split = section.split('Introdution', 1)
    if len(split) == 2: section = 'Introdution' + split[1]        
    return section, replacements  

@g_.app.route('/content_creator-remove-outline-bad-words', methods=['POST']) #type: ignore
async def RemoveBadWordsFromOutline():
    UpdateBlackLists()
    rqst                     = request.json                                #type: ignore              
    model                    = rqst['Model']                               #type: ignore   
    fixed_text, replacements = await __RemoveBadWordsFromOutline(rqst)    
    return jsonify({'Reply' : fixed_text, 'Replacements' : replacements})

async def OutlineFinalizeCeation(rqst):                                   #type: ignore              
    model                    = rqst['Model']                              #type: ignore   
    fixed_text, replacements = await __RemoveBadWordsFromOutline(rqst)             
    return {'Reply' : fixed_text, 'Replacements' : replacements}

def GetMissingLinksCount(user, assistant):
    def GetPromptLinks(user):
        prompt_links = []
        lines = user.splitlines()
        for index, line in enumerate(lines):
            if line.startswith('Link #') or line.startswith('"Link #'):
                try: 
                    url = lines[index+1].split('Target URL: ')[1]
                    prompt_links.append(url)
                except:                   
                    pass    
        #print(prompt_links)        
        return prompt_links       

    missing_count = 0
    found_links   = GetPromptLinks(user)
    for link in found_links:
        if f'({link})' not in assistant: missing_count += 1
    return missing_count        

class PooledContentCreator(Pooled):
    def __init__(self, name, section):
        super().__init__(f'PooledContentCreator_{name}', ['Generate'])
        self.Reply     = {}
        self.__section = section

    def Finish(self, err: str) -> None:
        self.Reply = {'role': 'assistant', 'content' : err}
    
    async def Dummy(self) -> str:
        return f'Placeholder reply for section {self.__section}'

    async def GenrateWithLinksCountCheck(self, messages, model, temp, user, base_url):
        reply         = await OpenRouterAChat(messages, model=model, temp=temp, user=user, base_url=base_url, dbug=self.IsDebugEnabled())
        _user         = messages[-1]['content']
        return reply
        if reply.startswith('Error calling Open Router API: '): return reply # let the caller handle it
        missing_links = GetMissingLinksCount(_user, reply)
        if missing_links == 0: return reply
        if missing_links > 0: 
            new_reply             = await OpenRouterAChat(messages, model=model, temp=temp, user=user, base_url=base_url)
            missing_links_2nd_try = GetMissingLinksCount(user, new_reply)
            return new_reply if missing_links_2nd_try < missing_links else reply
        return reply    

    async def Create(self, messages, model, temp):
        #postlog(self.BaseUrl(), self.UserId(), "About to send request", msgtype='AI Request')
        print("======================CREATE=====================")
        reply      = 'Error calling Open Router API: '
        found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
        count      = 0
        while reply.startswith('Error calling Open Router API: ') or not found_tags:
            #postlog(self.BaseUrl(), self.UserId(), "Sending request", msgtype='AI Request')
            #reply      = await OpenRouterAChat(messages, model=model, temp=temp, user=self.UserId(), base_url=self.BaseUrl())
            reply       = await self.GenrateWithLinksCountCheck(messages, model, temp, self.UserId(), self.BaseUrl())
            #postlog(self.BaseUrl(), self.UserId(), "Request sent", msgtype='AI Request')
            found_tags = True #if reply.find('<new>') > -1 and reply.find('</new>') > reply.find('<new>') else False
            count     += 1
            if count  == 4: break
        
        if self.IsDebugEnabled(): return reply
        return RemoveXMLTags(reply)  
        count = 0
        while reply.startswith('Error calling Open Router API: ') and count < 3:      
            reply = await OpenRouterAChat(messages, model=model, temp=temp) 
        return reply            
        
    async def Start(self, json: dict)-> None:
        query    = json['Query']                                                  #type: ignore
        messages = query['Messages']
        section  = query['Section']
        _type    = query['Type']
        model    = query['Model']
        #if self.IsDebugEnabled(): await self.Next(self.Dummy())                  #type: ignore 
        #else: await self.Next(self.Create(messages, model=model, temp=0.5))      #type: ignore
        await self.Next(self.Create(messages, model=model, temp=0.5))

@g_.app.route('/content_creator-create-polled', methods=['POST'])            #type: ignore    
async def CreatePolled():   
    print("content_creator-create-polled") 
    name    = request.json['Query']['Keyword'].replace(' ', '_')             #type: ignore 
   
    creator = PooledContentCreator(name, request.json['Query']['Section'] )  #type: ignore   
    #postlog(deepcopy(request.root_url), GetCurrentUserid(), f'Created pooled content creator for {name}', msgtype='AI Request')     
    #postlog(deepcopy(request.root_url), GetCurrentUserid(), f'Pooled content status {creator.GetStatus()}', msgtype='AI Request')     
    if creator.GetStatus() == STATUS.NOT_POOLED:           
        return jsonify({'Err' : STATUS.NOT_POOLED})
    creator.Run(request.json)                                                #type: ignore  
    return jsonify({'Reply' : creator.serialize()})       

async def ImproveArticle(request): 
    sys     = request['System']   
    user    = request['User']   
    article = request['Article'] 
    model   = request['Model']
    if IsDebugEnabled(): return jsonify({'Reply' : 'IMPROVED PLACEHOLER FOR: ' + article, 'System' : sys, 'User' : user})
    #if IsDebugEnabled(): return jsonify({'Reply' : sys + '\n\n' + user, 'System' : sys, 'User' : user})
    msgs = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]
    reply = await OpenRouterAChat(msgs, model=model, temp=0.5)
    return jsonify({'Reply' : reply, 'System' : sys, 'User' : user})
    return jsonify({'Reply' : RemoveTagsB(reply), 'System' : sys, 'User' : user})



    intent  = request['Search Intent']   
    article = request['Article']    
    aud     = request['Audience']
    outline = request['Outline']
    model   = request['Model']
    tones   = ''.join([f'{t},' for t in request['Tones']]).strip(',')
    links   = request['Links']
    sys     = PROMPT.CONTENT_IMPROVE_SYSTEM_NO_LINKS.format(outline, intent) if links == '' else PROMPT.CONTENT_IMPROVE_SYSTEM.format(links, outline, intent)
    user    = PROMPT.CONTENT_IMPROVE_USER.format(tones, aud, article)
    if IsDebugEnabled(): return jsonify({'Reply' : article, 'System' : sys, 'User' : user})
    #if IsDebugEnabled(): return jsonify({'Reply' : sys + '\n\n' + user, 'System' : sys, 'User' : user})
    msgs = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}   
    ]
    reply = await OpenRouterAChat(msgs, model=model, temp=0.5)
    return jsonify({'Reply' : RemoveTagsB(reply), 'System' : sys, 'User' : user})

async def GenTitlesAndMetadescription(request):
    kword   = request['Keyword']
    Outline = request['Outline']
    intent  = request['Search Intent']
    system  = request['System']
    user    = request['User']
    today   = request['Today']
    print(system, user)
    if IsDebugEnabled(): return jsonify({'Reply' : 'Placeholder Title and metadescription\n'})
    msgs = [
        {
            'role'    : 'system', 
            'content' :  system.replace('{KEYWORD}', kword).replace('{SEARCH_INTENT}', intent).replace('{OUTLINE}', Outline).replace("{DATE}", today)
        },
        {   'role'    : 'user', 
            'content' :  user.replace('{KEYWORD}', kword).replace('{SEARCH_INTENT}', intent).replace('{OUTLINE}', Outline).replace("{DATE}", today)
        }  
    ]
    reply = await OpenRouterAChat(msgs, model=request['Model'], temp=0.9)
    #print(reply)
    return jsonify({'Reply' : reply})   


async def GenCTA(json, kword_data):
    print(kword_data)
    sys          = json['System']
    user         = json['User']    
    model        = json['Model']
    content      = kword_data['text']
    kword        = kword_data['Keyword']
    client       = kword_data['CTA']['Client']
    service_name = kword_data['CTA']['ServiceName']
    service_desc = kword_data['ServiceDescription']
    service_inst = kword_data['ServiceInstructions']
    replacements = {'{KEYWORD}' : kword, '{CLIENT}' : client, '{SERVICE_NAME}' : service_name, '{SERVICE_DESCRIPTION}' : service_desc, 
                    '{SERVICE_INSTRUCTIONS}' : service_inst, '{CONTENT}' : content}
    for key, val in replacements.items():
        print(key, val)
        sys  = sys.replace(key, val)
        user = user.replace(key, val)
    msgs = [
        {'role' : 'system', 'content' : sys},
        {'role' : 'user', 'content'   : user}
    ]
    print("==============================================", model)
    assistant = 'Error calling Open Router API: '        
    count     = 0
    while assistant.startswith('Error calling Open Router API: '):        
        assistant  = await OpenRouterAChat(msgs, model=model, temp=0.6)        
        count     += 1
        if count  == 4: break
    return {'Keyword' : kword, 'Index' : kword_data['index'], "Assistant" : assistant}

@g_.app.route('/content-creator-gen-ctas', methods=['POST'])
async def GenCTAs():   
    if ''  == GetCurrentUserid(): return await flask_templace('login') 
    for section in  request.json["Sections"]: print(section)                                            #type: ignore
    replies = await gather( *[GenCTA(request.json, section) for section in request.json["Sections"]] )  #type: ignore
    return jsonify({'Replies' : replies})

def Trim(string: str) -> str:
    string = string.replace('\n', '').replace('\r', '').strip('-')  
    return string.strip() 

def RemoveSectionNumbers(string):
    if match(r'-*\s*[*]*\s*[0-9.\s]+', string): string = sub(r'-*\s*[*]*\s*[0-9.\s]+', '', string, 1)                
    if match(r'-*\s*Q[0-9]:', string):          string = sub(r'-*\s*Q[0-9]:', '', string, 1)    
    return string    

def Prefix(split, curr_index):
    if curr_index > 0:
        prev = split[curr_index-1]   
        if prev.strip().lower().startswith(f'introduction'): return '___Introduction___: '        
        if prev.strip().lower().startswith(f'conclusion'): return '___Conclusion___: '    
        if RemoveSectionNumbers(prev).strip().lower().startswith(f'conclusion'): return '___Conclusion___: '    
    return '' 

def TrimSection(section):
    sec_len = 120
    return section[0:sec_len-3] + '...' if len(section) > sec_len else section    

def ParseSection(section):
    if section.startswith('Introduction-Tag'):
        return 'Introduction: ' + section.split('Introduction-Tag')[1]    
    if section.startswith('Conclusion-Tag['):
        split = section.split('Conclusion-Tag[')
        if len(split) == 2:
            if split[1].find(']') > 0:
                if split[1].split(']')[0].isnumeric():
                    index  = split[1].split(']')[0]
                    prefix = f'Conclusion-Tag[{index}]'
                    return f'{index}. Conclusion{section.split(prefix)[1]}' 
    #return section                   
    if section.startswith('FAQ-TAG['):
        split = section.split('FAQ-TAG[')
        if len(split) == 2:
            if split[1].find(']') > 0:
                if split[1].split(']')[0].isnumeric():
                    index  = split[1].split(']')[0]
                    prefix = f'FAQ-TAG[{index}]'
                    return f'{index}. Frequently Asked Questions: {section.split(prefix)[1]}'          
                    return f'{index}. FAQ: {section.split(prefix)[1]}'                 
    return section       

def GetIndex(string, last_index):
    index = ''
    for char in string:
        if not char.isnumeric() or char == '.':
            break
        index += char     
    return int(index) if index != '' else last_index    

def ExcludeSubsections(sections):
    new_sections = []    
    for section in sections:
        try:
           prefix = section.split(' ')[0].strip()
           if prefix.count(".") > 1: continue
           new_sections.append(section)
        except (IndexError):
            new_sections.append(section)
    return new_sections        


    new_sections = []    
    for section in sections:
        try:
           prefix = section.split(' ')[0].strip().strip('.')
           #if prefix[0].isnumeric() and len(prefix) > 1: continue
           if prefix[0].isnumeric() and prefix[1].isnumeric() > -1: continue
           new_sections.append(section)
        except (IndexError):
            new_sections.append(section)
    return new_sections        

def ExcudeBriefs(outline):
    new_outline = ''
    split       = outline.splitlines()
    max_index   = len(split)-1
    briefs      = []
    for index, line in enumerate(split):
        if line.strip().lower().startswith('- brief'):
            briefs.append(line)
            if index > 1 and index < max_index: continue
        new_outline += line + '\r\n' 
    return briefs, new_outline + '\n\n'  #add line breaks to fix missing conclusion when there is no content in the conclusion       

def GetBrief(split, section):    
    for index, line in enumerate(split):
        if line.strip().lower() == section.strip().lower():
            try: 
                return split[index+1]
            except(IndexError):  return ''
    return ''    

def MergeSubsections(sections):   
    merged = []
    for section in sections:
        if section.startswith('Introduction-Tag'): merged.append(section)
        elif section.startswith('Conclusion-Tag'): merged.append(section)
        elif section.startswith('FAQ-TAG['): merged.append(section)
        elif len(section.split('.')) >= 2:
            if section.split('.')[1].isnumeric() and len(merged) > 0: merged[-1] += '\r\n' + section
            else: merged.append(section)
               
    return merged     

def IpprovedOutlineSectionSpliter(outline_arg, merge_subsections):
    last_index            = 0
    on_faq                = ''
    faq                   = 'frequently asked questions'    
    new_outline           = ''
    tag                   = ':section_start_tag:'
    orig_split            = outline_arg.splitlines()    
    outline               = outline_arg + '\n\n'      
    exclusion_tag         = False
    split                 = outline.splitlines()    
    for index, line in enumerate(split):       
        line       = Trim(line)      
        #if line == '': continue  
        oring_line = line
        line       = tag + Prefix(split, index) + line if not on_faq else RemoveSectionNumbers(line) + '@@@@@'
        exclusion_tag = False  
        no_numbers = RemoveSectionNumbers(oring_line)        
        if no_numbers.lower().startswith(faq) or no_numbers.lower().startswith(f'{tag}{faq}'): 
            line   = f'FAQ-TAG[{last_index+1}]@@@@@'
            on_faq = True            
        else:
            if len(oring_line) > 0 and not on_faq: last_index = GetIndex(oring_line, last_index)                  
        if line.startswith(f'{tag}Introduction')  or line.startswith(f'{tag}Conclusion') \
            or line.startswith('Introduction')    or line.startswith('Conclusion'):           
            exclusion_tag  = True 
            on_faq         = False
        line = line.replace('___Introduction___', 'Introduction-Tag')     
        line = line.replace('___Conclusion___', f'Conclusion-Tag[{last_index+2}]')     
        if exclusion_tag == False: new_outline += line + '\r\n'                
    tagged  = [s for s in [Trim(string) for string in new_outline.split(tag)] if len(s) and not s.startswith('## TABLE OF CONTENT')] 
    t       = tagged
    if merge_subsections:       
       tagged = ExcludeSubsections(tagged) #MergeSubsections(tagged)
    plain   = [ParseSection(s).replace('@@@@@', '\r\n-').strip('\r\n-') for s in tagged]  
    trimed  = [TrimSection(s) for s in plain]     
    merged  = MergeSubsections(t)        
    return {'Tagged' : tagged, 'Trimed' : trimed, 'Plain' : plain, 'Merged' : merged}

def GetSubSections(sections, section):
    subsections = ''
    try:
        prefix = [item for item in section.split(' ')[0].split('.') if item != '']
        #print(prefix)
        for s in sections:
            p = [item for item in s.split(' ')[0].split('.') if item != '']
            if len(p) == len(prefix) + 1:
                if p[0:-1] == prefix:                    
                    subsections += s + '\n'
        return subsections.strip()          

    except(IndexError):
        return 'IndexError'        

async def StartChat(query, merge_subsections):   
    #print(query)
    claude = query['Claude']
    tone   = f'the tone "{query["Tones"][0]}"' if len(query['Tones']) == 1 else f'a mix of the tones \"{query["Tones"][0]}\" and "{query["Tones"][0]}"'
    tones  = ''.join([f'{t},' for t in query['Tones']]).strip(',')
    system = PROMPT.CONTENT_CREATOR_INITIAL_SYSTEM.format(query['Keyword'], query['SearchIntent'], query['Outline'], query['Audience'], tones, query['Facts'], tones, query['Audience']) 
    tone   = f' {query["Tones"][0]}' if len(query['Tones']) == 1 else f's \"{query["Tones"][0]}\" and "{query["Tones"][1]}"'    
    user   = PROMPT.GetIntroUser(claude, query["Tones"]).format(query['Keyword'], 
        query['SearchIntent'], 
        query['Audience'],
        tone, 
        query['Outline']
        ) if claude == False else PROMPT.GetIntroUser(claude, query["Tones"]).format(query['Keyword'], 
        query['SearchIntent'], 
        query['Audience'],       
        query['Outline']
        )
    chat   = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}] 
    if merge_subsections :system = system.replace(', without including its subsections', '') 
    if IsDebugEnabled(): chat.append({'role': 'assistant', 'content': 'Introduction placeholder'})
    else               : chat.append({'role': 'assistant', 'content': await OpenRouterAChat(chat, model=query['Model'], temp=0.5)})
    return {'Chat' : chat, 'Sections' : IpprovedOutlineSectionSpliter(query['Outline'], merge_subsections)} 

async def DoConclusion(query, claude):
    conclusion = query["PlainSection"].split('Conclusion')[0] if query["PlainSection"].startswith('Conclusion') else query["PlainSection"]
    system = PROMPT.GetConclusionSystem(claude, query["Tones"]).format(
        conclusion, 
        query['Audience']) if claude == False else PROMPT.GetConclusionSystem(claude, query["Tones"]).format(
            query['Audience'],            
            conclusion
        )   
    user   = PROMPT.GetConclusionUser(claude).format(conclusion)
    chat   = query['Chat']
    chat.append({'role' : 'system', 'content' : system})
    chat.append({'role' : 'user', 'content' : user})
    if IsDebugEnabled(): chat.append({'role' : 'assistant', 'content' : 'conclusion placeholder'})
    else               : chat.append({'role' : 'assistant', 'content'  : await OpenRouterAChat(chat, model=query['Model'], temp=0.5)})
    return {'Chat' : chat} 

async def DoFaq(query, claude):
    system = PROMPT.GetFAQSystem(claude).format(query['PlainSection'], query['PlainSection'], query['PlainSection'])   
    user   = PROMPT.GetFAQUser(claude).format(query["PlainSection"])
    chat   = query['Chat']
    chat.append({'role' : 'system', 'content' : system})
    chat.append({'role' : 'user', 'content' : user})
    if IsDebugEnabled(): chat.append({'role' : 'assistant', 'content' : 'FAQ placeholder'})
    else               : chat.append({'role' : 'assistant', 'content'  : await OpenRouterAChat(chat, model=query['Model'], temp=0.5)})
    return {'Chat' : chat}     

async def DoSection(query, claude):     
    if query['MergeSubsections']: links_list = [l for l in query['Links'] if l["Section"][0].isnumeric() and l["Section"][0] == query['TaggedSection'][0]]
    else                        : links_list = [l for l in query['Links']]
    subsections = GetSubSections(query['Sections'], query['TaggedSection'])
    if subsections != '':
        subsections = 'Do not write about the following subsections (I will send you an instruction to cover them later): ' + subsections
    links  = ''.join([f'Link {i+1}:\nTarget URL: {l["TargetURL"]}\nAnchor text: {l["Anchor"]}\nSection: {l["Section"]}\n' for i, l in enumerate(links_list)])
    system = PROMPT.GetSectionSystem(claude, links, query['Tones']).format(
        query['TaggedSection'],       
        query['TaggedSection'],
        subsections,
        links, 
        query['Audience']) if claude == False else PROMPT.GetSectionSystem(claude, links, query['Tones']).format(           
            query['Audience'],            
            query['TaggedSection'], 
            query['TaggedSection'])   
    if query['MergeSubsections']:
        system = system.replace('and format the entire content using Markdown syntax', 'and its subsections. Do not write about the following sections')
    user = PROMPT.GetSectionUser(claude, links, query['Tones']).format(
        query['TaggedSection'], 
        links
        ) if claude == False else PROMPT.GetSectionUser(claude, links, query['Tones']).format(query['TaggedSection'])  
    chat = query['Chat']
    chat.append({'role' : 'system', 'content' : system})
    chat.append({'role' : 'user', 'content' : user})
    if IsDebugEnabled(): chat.append({'role' : 'assistant', 'content' : 'section placeholder'})
    else               : chat.append({'role' : 'assistant', 'content'  : await OpenRouterAChat(chat, model=query['Model'], temp=0.5)})
    return {'Chat' : chat} 

def IsSectionNumber(s):
    for char in s:
        if not char.isnumeric() and not char == ".": return False
    return True  

def RemoveTags(s, query):  
    for msg in s['Chat']:
        if msg['role'] == 'assistant':           
            msg['content'] = sub(r'#\s[0-9.]+\s', '# ', msg['content'], 0)    
    return s    

    for msg in s['Chat']:
        if msg['role'] == 'assistant':
            msg['content'] = msg['content'].replace('<INTROCUCTION>', '').replace('</INTROCUCTION>', '').replace('<SECTION>', '').replace('</SECTION>', '') 
            if msg['content'].find('#') > -1: msg['content'] = '#' + msg['content'].split("#", 1)[1]
            if msg['content'].startswith('Here is the introductory paragraph') and msg['content'].find(':\n') > 1:  msg['content'] = msg['content'].split(":\n", 1)[1]
            if msg['content'].find(' ') > -1:
                split = msg['content'].strip().split(' ') 
                if len(split) >= 2:
                    if IsSectionNumber((split[1]).strip()):
                        msg['content'] = msg['content'].replace(f' {split[1].strip()} ', ' ', 1)    
            if msg['content'].find(' ') > -1:
                split = msg['content'].strip().split(' ') 
                if len(split) >= 2:
                    if IsSectionNumber((split[0]).strip()) and (split[1].strip().lower() == 'conclusion' or split[1].strip().lower() == 'faq'):
                        msg['content'] = msg['content'].replace(f'{split[0].strip()} ', '', 1)                         
    return s           

async def NextSextion(query):    
    claude = query['Claude']
    if   query['TaggedSection'].startswith('FAQ-TAG[')         : return RemoveTags(await DoFaq(query, claude), query)        if claude is False else RemoveTags(await DoFaq(query, claude), query)
    elif query['TaggedSection'].startswith('Conclusion-Tag[' ) : return RemoveTags(await DoConclusion(query, claude), query) if claude is False else RemoveTags(await DoConclusion(query, claude), query) 
    return RemoveTags(await DoSection(query, claude), query) if claude is False else RemoveTags(await DoSection(query, claude), query)   
