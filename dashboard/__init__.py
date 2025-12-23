'''
commands:
flask --app dashboard --debug run --host=0.0.0.0
cloudron build --url 'https://build.flawlessmarketing.com' --build-token ??????
cloudron update image ?????

cloudron update will print the image name to use in the update step
'''


print('version: 10/01/2025 - 14:08')
from flask import Flask, render_template_string, request, jsonify, redirect, make_response
from json import dumps
from aiofile import async_open
from os import listdir, getenv
from os.path import isfile, join, dirname, realpath
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_login.mixins import AnonymousUserMixin 
from dashboard.database import Database
from dotenv import load_dotenv
from dashboard.constants import ACCESS, GetTones, GetAudiences, CONTENT_GEN_DEFAULT, CONTENT_GEN_LEGACY
load_dotenv()
from os import environ
from pathlib import Path
from os.path import expanduser
from os import chmod
from tempfile import gettempdir
print('Path.Home()', str(Path.home()))
print("Epanduser", expanduser('~'))
environ['HF_HOME']            = gettempdir()
environ['TRANSFORMERS_CACHE'] = gettempdir()
from dashboard.OutlineGen import serp, ScrapeURLs, GenSearchIntent, GenerateOutline, GenerateOptmizedOutline, CleanUPOutline, GenerateOptmizedOutlineWithFacts
from dashboard.app import g_, IsAdmin, err, template, flask_templace, GetCurrentUserid, SetDebugFlag, IsDebugEnabled
from asyncio import gather, sleep as async_sleep
from dashboard.topic_cluster_creator import GenerateEntities, EntityAnalysis, EntityAnalysisOpenRouter, GenerateAnchors, GenerateAnchorsOpenRouter, GenFacts
from json import dumps
from dashboard.similarity import ClusterSimilarity
from threading import Thread
from datetime import timedelta
from dashboard.content_creator import IpprovedOutlineSectionSpliter, StartChat, NextSextion, GenTitlesAndMetadescription, RemoveTagsB, ImproveArticle, OutlineFinalizeCeation
from dashboard.ChatGpt import OpenRouterAChat
from json import loads
from pandas import read_csv
from io import StringIO
from dashboard.guest_posting import CreateGuestPost 
import dashboard.dataset_tunning
from dashboard.alchemy import init_database, AlchemyLogs
from dashboard.RTNews import RTNews_get

class User(UserMixin): pass

@g_.auth.user_loader
def user_loader(email):
    if False == g_.db.IsUserEmail(email): return
    user    = User()
    user.id = email #type: ignore 
    return user

@g_.auth.request_loader
def request_loader(request):    
    return user_loader(request.form.get('email'))

@g_.app.route('/admin', methods=['GET', 'POST'])    
async def admin():
    if ''    == GetCurrentUserid(): return await flask_templace('login')    
    if False == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return '<h4>You\'re not an admin</h4>'
    #print(request.form)
    page = request.args.get('page')
    return await flask_templace(page, user='user.png', admin=True)  

@g_.app.route('/seo_tool', methods=['GET', 'POST'])    
async def seo_tool():    
    #print(request.form)
    page  = request.args.get('page')    
    flags = g_.db.GetUserByEmail(GetCurrentUserid())['access_flags']   
    flags = 0xfff  
    OUTLINE = flags & 0x00000001
    CLUSTER = flags & 0x00000002
    ENTITY  = flags & 0x00000004
    DOMAIN  = flags & 0x00000008
    ARTICLE = flags & 0x00000010
    LINKS   = flags & 0x00000020
    GUEST   = flags & 0x00000040
    TUNING  = flags & 0x00000080
    AIWORD  = flags & 0x00000100
    dbug    = flags & 0x10000000
    return await flask_templace(
        page, 
        user='user.png', 
        admin=IsAdmin(), 
        page                       = str(page),
        acess_flag_outline_gen     = OUTLINE, 
        acess_flag_cluster_creator = CLUSTER,
        acess_flag_entity_gen      = ENTITY, 
        acess_flag_domain_filter   = DOMAIN,
        acess_flag_article_gen     = ARTICLE,
        acess_flag_links_gen       = LINKS,
        acess_flag_dbug            = dbug,
        acess_flag_guest_posting   = GUEST,
        acess_flag_dset_tuning     = TUNING,
        acess_flag_ai_words        = AIWORD,
        colors                     = g_.colors
    )      

@g_.app.route('/logout')    
async def logout():
    logout_user()
    return redirect('/')

@g_.app.route('/login', methods=['POST'])   
async def login():
    class freeuser(User):
        @property
        def is_active(self):
            return True
        def get_id(self):
            return 'freeuser'
    
    login_user(freeuser(), remember=True, duration=timedelta(days=30))
    return jsonify({}) 
    data = request.json
    if data == None: return err('User no found')    
    if g_.db.IsUser(data['user_name']): 
       user = g_.db.GetUser(data['user_name']) 
       if user == False: return err('User no found')    
       if data['password'] == user['password']: 
            login    = User()
            login.id = user['email'] #type: ignore 
            login_user(login, remember=True, duration=timedelta(days=30))
            return jsonify(data) 
       else: return err('Wrong password')                     
    return err('User no found')     

@g_.app.route('/register', methods=['POST'])   
async def register():    
    data = request.json
    for key in ['user_name', 'email', 'password']:
        if data[key] == '':                                                               #type: ignore 
            k = key.replace('_', ' ')
            return jsonify({'err' : f'Missing {k}'})
    if len(data['password']) < 4:                                                         #type: ignore 
        return jsonify({'err' : f'Password must be at least four characters long'})        
    if g_.db.IsUserEmail(data['email']):                                                  #type: ignore 
        return jsonify({'err' : f'Email already registered'})
    if g_.db.IsUser(data['user_name']):                                                   #type: ignore 
        return jsonify({'err' : f'User name already taken'})
    
    g_.db.AddUser(data['user_name'], data['email'], data['password'])                     #type: ignore  
    user    = User()
    user.id = data['email']                                                               #type: ignore 
    login_user(user, remember=True, duration=timedelta(days=30))
    return jsonify(data)    

@g_.app.route("/")
async def main():       
    #print(g_.db.GetUsers())
    if '' == GetCurrentUserid(): return await flask_templace('login')     

    admin = g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN
    dbug  = g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.DBUG    
    return await flask_templace('main', user='user.png', admin=admin,  colors=g_.colors, acess_flag_dbug=dbug)
    
@g_.app.route("/admin-get-logs-keys", methods=['POST'])             #type: ignore 
async def admin_get_logs_keys():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    if False == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return jsonify({'Err' : "NOT ADMIN"})
    logs = AlchemyLogs().GetKeys()    
    return jsonify(logs) 

@g_.app.route("/admin-get-user-logs", methods=['POST'])             #type: ignore 
async def admin_get_user_logs():
    if    '' == GetCurrentUserid(): return await flask_templace('login')     
    if False == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return jsonify({'Err' : "NOT ADMIN"})
    user     = request.args.get('User')
    #print(user)
    logs = AlchemyLogs().GetLogs(user, request.json['Functions'], request.json['Types'])     #type: ignore 
    #print(logs)
    return jsonify({'Logs' : logs})  

@g_.app.route('/admin-delete-log', methods=['POST'])
async def admin_delete_log():
    if    '' == GetCurrentUserid(): return await flask_templace('login')     
    if False == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return jsonify({'Err' : "NOT ADMIN"})
    user      = request.json['User']          #type: ignore 
    func      = request.json['Func']          #type: ignore 
    timestamp = request.json['Timestamp']     #type: ignore    
    AlchemyLogs().DeleteLog(user, func, timestamp)
    return jsonify({})

@g_.app.route('/log-exception', methods=['POST'])
async def LogClientException():
    if    '' == GetCurrentUserid(): return await flask_templace('login')     
    if False == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return jsonify({'Err' : "NOT ADMIN"})    
    AlchemyLogs().log(GetCurrentUserid(), dumps(request.json, indent=4), 'Client Exception')
    return jsonify({})


#==================================================================================
#================================SETTINGS==========================================
#==================================================================================

@g_.app.route("/settings-get", methods=['POST'])    #type: ignore       
async def settings_get(): 
    if ''     == GetCurrentUserid(): return await flask_templace('login')     
    rqst        = request.json['Request']           #type: ignore 
    setttings   = g_.db.LoadCluster(GetCurrentUserid(), rqst['SettingsID'])
    g_setttings = g_.db.LoadCluster(g_.SharedDataID, rqst['SettingsID'])
    if not isinstance(g_setttings, dict): g_setttings = loads(g_setttings) #type: ignore  
    if 'err' in g_setttings:
        tasks       = ['outline-generation', 'outline-cleaning', 'search-intent', 'content', 'entities', 'anchors', 'improve-content', "facts", 
        'titles', 'black-list', 'outline-black-list', 'black-list-2nd', 'outline-black-list-2nd', 'self-referencing', 'guest-article', 'highlight',
        'links-insertion', 'CTAS']
        g_setttings = {'Models' : {task : 'anthropic/claude-instant-1' for task in tasks}}
    if not isinstance(setttings, dict)  : setttings = loads(setttings)         #type: ignore  
    if 'err' in setttings: setttings = g_setttings      
    #return jsonify({'Settings' : setttings})                                  #type: ignore       
    setttings['Models'] = g_setttings['Models']                                #type: ignore 
    if 'Prompts'      in g_setttings: setttings['Prompts']      = g_setttings['Prompts'] #type: ignore   
    if 'More Prompts' in g_setttings: setttings['More Prompts'] = g_setttings['More Prompts'] #type: ignore   
    #print(g_setttings.keys())
    #print(g_setttings['Models'])
    return jsonify({'Settings' : dumps(setttings)}) 

@g_.app.route("/settings-set", methods=['POST'])    #type: ignore 
async def settings_set():      
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst   = request.json['Request']                #type: ignore
    g_.db.WriteCluster(GetCurrentUserid(), rqst['SettingsID'], dumps(rqst['Data']))
    g_.db.WriteCluster(g_.SharedDataID, rqst['SettingsID'], dumps(rqst['Data']))
    return jsonify({'Reply' : ''})     

@g_.app.route("/settings-append-tone", methods=['POST'])      #type: ignore 
async def settings_append_tone():      
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst     = request.json['Request']                        #type: ignore
    new_tone = rqst['New Tone']    
    tones    = g_.db.LoadCluster(g_.SharedDataID, g_.TonesID)    
    if ('err' in loads(tones)) : tones = {}                   #type: ignore    
    else                       : tones = loads(tones)         #type: ignore       
    tones |= {new_tone['Tone'] : new_tone['Description']}    
    g_.db.WriteCluster(g_.SharedDataID, g_.TonesID, dumps(tones))
    return jsonify({'Reply' : ''}) 

@g_.app.route("/settings-append-audience", methods=['POST'])    #type: ignore 
async def settings_append_audience():     
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst         = request.json['Request']                      #type: ignore
    new_audience = rqst['New Audience']
    audiences    = g_.db.LoadCluster(g_.SharedDataID, g_.AudiencesID)
    if ('err' in audiences)       : audiences = {}                #type: ignore
    else                          : audiences = loads(audiences)  #type: ignore    
    audiences |= {new_audience['Audience'] : new_audience['Description']}
    g_.db.WriteCluster(g_.SharedDataID, g_.AudiencesID, dumps(audiences))
    return jsonify({'Reply' : ''})   

@g_.app.route("/settings-delete-tone", methods=['POST'])     #type: ignore 
async def settings_del_tone():      
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    say_goodby_to = request.json['Tone']                     #type: ignore 
    tones         = g_.db.LoadCluster(g_.SharedDataID, g_.TonesID)
    if ('err' in loads(tones)): tones = {}                   #type: ignore
    else                      : tones = loads(tones)         #type: ignore
    tones.pop(say_goodby_to, None)
    g_.db.WriteCluster(g_.SharedDataID, g_.TonesID, dumps(tones))
    return jsonify({'Reply' : ''})     

@g_.app.route("/settings-delete-aud", methods=['POST'])     #type: ignore 
async def settings_del_aud():      
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    say_goodby_to = request.json['Aud']                     #type: ignore 
    auds          = g_.db.LoadCluster(g_.SharedDataID, g_.AudiencesID)
    if ('err' in loads(auds)): auds = {}                    #type: ignore
    else                     : auds = loads(auds)           #type: ignore
    auds.pop(say_goodby_to, None)
    g_.db.WriteCluster(g_.SharedDataID, g_.AudiencesID, dumps(auds))
    return jsonify({'Reply' : ''})        

#==================================================================================
#================================ADMIN ROUTES======================================
#==================================================================================

@g_.app.route('/list_users', methods=['POST'])
async def list_users():
    users = {user['user_name'] : {'email' : user['email'], 'access_flags' : user['access_flags']} for user in g_.db.GetUsers()}
    #users = {f'user{i}' : {'email' : f'email{i}', 'access_flags' : 0xff} for i in range(1_000)}
    return jsonify(users)

@g_.app.route('/get_user', methods=['POST']) 
async def get_user():
    user_name = request.args.get('user_name')
    if False == IsAdmin(): return err('Not admin')
    user      = g_.db.GetUser(user_name)
    if False == user: return err('bad user name')
    user.pop('password', None) #type: ignore 
    return jsonify( user )   

@g_.app.route('/delete_user') 
async def delete_user():
    user_name = request.args.get('user_name')
    if False == IsAdmin(): return err('Not admin')
    user      = g_.db.GetUser(user_name)
    if False == user: return err('bad user name')
    g_.db.RemoveUser(user['user_name'], user['email']) #type: ignore 
    return await flask_templace('Users', user='user.png', admin=True)  

@g_.app.route('/set_user_acess_flags', methods=['POST']) 
async def set_user_acess_flags():
    user_name   = request.args.get('user_name')
    email       = request.args.get('email')
    acess_flags = request.args.get('access_flags')
    if False == IsAdmin()              : return err('Not admin')
    if False == g_.db.IsUser(user_name): return err('bad user name')
    if False == user_name              : return err('bad user name')
    g_.db.SetUserAcessFlags(email, acess_flags)
    return await get_user() 

@g_.app.route('/set_user_debug_enabled', methods=['GET'])
async def set_user_debug_enabled():     
    #print(request.args.get('dbug_flag'))
    SetDebugFlag(request.args.get('dbug_flag'))   
    return await main()   

#==================================================================================
#=============================OUTLINE GEN ROUTES===================================
#==================================================================================   

@g_.app.route('/outlinegen-get-tones', methods=['POST']) 
async def outline_get_tones():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    reply = {'Tones' : GetTones(), 'Audiences' : GetAudiences()}
    additional_tones     = g_.db.LoadCluster(g_.SharedDataID, g_.TonesID)     #type: ignore 
    additional_audiences = g_.db.LoadCluster(g_.SharedDataID, g_.AudiencesID) #type: ignore 
    if not isinstance(additional_tones, dict)    : additional_tones     =  loads(additional_tones)
    if not isinstance(additional_audiences, dict): additional_audiences =  loads(additional_audiences)
    if 'err' not in additional_tones.keys():        
        for tone, caption in additional_tones.items():
            for index, item in enumerate(reply['Tones']):
                if item['Tone'] == tone:
                    reply['Tones'].pop(index)
                    break
            reply['Tones'].append( {'Tone' : tone, 'Caption' : caption} )    
    if 'err' not in additional_audiences.keys():        
        for tone, caption in additional_audiences.items():            
            for index, item in enumerate(reply['Audiences']):
                if item['Audience'] == tone:
                    reply['Audiences'].pop(index)
                    break   
            reply['Audiences'].append( {'Audience' : tone, 'Caption' : caption} )         
    return jsonify(reply) 

@g_.app.route('/outlinegen-gen-intent', methods=['GET', 'POST'])
async def outline_gen_gen_intent():  
    if '' == GetCurrentUserid(): return await flask_templace('login')      
    country  = request.args.get('country_code')
    keyword  = request.args.get('keyword') 
    model    = request.args.get('model')   
    intent   = 'PLACE HOLDER'
    if IsDebugEnabled(): return jsonify({'Reply' : intent})      
    
    intent = await GenSearchIntent(country, keyword, model, None)    
    return jsonify({'Reply' : intent})         

@g_.app.route('/outlinegen-serp-all', methods=['POST'])
async def outline_gen_serp_all():
    if '' == GetCurrentUserid(): return await flask_templace('login')   
    data      = request.json  
    country   = data['CountryCode'] #type: ignore 
    keywords  = data['Keywords']    #type: ignore 
    model     = data['Model']       #type: ignore 
    prompts   = data['Prompts']     #type: ignore
    #print(keywords, country, IsDebugEnabled())
    urls    = [[f'{kword} Placeholder Link {i}' for i in range(10)] for kword in keywords]    
    reply   = [{'Keyword' : kword, 'URLs' : urls, 'intent' : f'Search Intent placeholder for {kword}'} for kword, urls in zip(keywords, urls)]
    if IsDebugEnabled(): return jsonify({'Reply' : reply})  
    
    urls    = await gather( *[serp(country, kword) for kword in keywords] )
    intents = await gather( *[GenSearchIntent(country, kword, model, prompts['Search Intent']) for kword in keywords] )
    reply = [{'Keyword' : kword, 'URLs' : urls, 'intent' : intent} for kword, urls, intent in zip(keywords, urls, intents)]    
    return jsonify({'Reply' : reply})       

@g_.app.route('/outlinegen-serp', methods=['POST'])
async def outline_gen_serp():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    country  = request.args.get('country_code')
    keyword  = request.args.get('keyword') 
    model    = request.args.get('model')   
    #print(country, keyword, model)  
    urls = [f'{keyword} Placeholder Link {i}' for i in range(10)]
    if IsDebugEnabled(): return jsonify({'URLs' : urls, 'intent' : f'Search Intent placeholder for {keyword}'})  
    return jsonify({'URLs' : await serp(country, keyword), 'intent' : await GenSearchIntent(country, keyword, model, None)}) #type: ignore   

@g_.app.route('/outlinegen-clean-up-all', methods=['POST'])
async def outline_gen_clean_up_all():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    data          = request.json
    Model         = data['Model']        #type: ignore    
    del data['Model']                    #type: ignore  
    #print(Model) 
    #print("===", [kword for kword in data])
   
    flat_urls           = []   
    flat_kwords         = []   
    flat_dirty_outlines = [] 
    for kword in data:                   #type: ignore 
        if kword == 'System' or kword == 'User': continue
        for entry in data[kword]:        #type: ignore 
            flat_urls.append(entry['url'])
            flat_dirty_outlines.append(entry['outline'])
            flat_kwords.append(kword)       

    reply = {}
    flat_outlines = [f'Clean {outline} {url}' for outline, url in zip(flat_dirty_outlines, flat_urls)]    
    if IsDebugEnabled() == False: flat_outlines = await gather(*[CleanUPOutline(kword, outline, Model) for kword, outline in zip(flat_dirty_outlines, flat_kwords)])
    for key, url, outline in zip(flat_kwords, flat_urls, flat_outlines):
        if key not in reply.keys(): reply[key] = {'URLs' : []}
        reply[key]['URLs'].append({'URL' : url, 'Outline' : outline})    
    return jsonify(reply)   

@g_.app.route('/outlinegen-scrape-all', methods=['POST'])
async def outline_gen_scrape_all():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    data    = request.json
   
    flat_urls   = []   
    flat_kwords = []   
    for kword in data:               #type: ignore 
        for url in data[kword]:      #type: ignore 
            flat_urls.append(url)
            flat_kwords.append(kword)       

    reply = {}
    flat_outlines = [f'Placeholder outline for {url}' for url in flat_urls]
    if IsDebugEnabled() == False: flat_outlines = await ScrapeURLs( flat_urls )
    for key, url, outline in zip(flat_kwords, flat_urls, flat_outlines):
        if key not in reply.keys(): reply[key] = {'URLs' : []}
        reply[key]['URLs'].append({'URL' : url, 'Outline' : outline}) 
    print('outline_gen_scrape_all finished')
    return jsonify(reply)         

@g_.app.route('/outlinegen-scrape', methods=['POST'])
async def outline_gen_scrape():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    data     = request.json
    response = [{'URL' : url, 'Outline' : f'Placeholder outline for {url}'} for url in data['URLs']]    #type: ignore 
    if IsDebugEnabled(): return jsonify({'URLs' : response})  
    outlines = await ScrapeURLs( data['URLs'] )                                                         #type: ignore 
    response = [{'URL' : url, 'Outline' : outline} for url, outline in zip(data['URLs'], outlines)]     #type: ignore 
    return jsonify({'URLs' : response})  

@g_.app.route('/outlinegen-generate', methods=['POST'])
async def outline_gen_generate():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    data   = request.json      
    if IsDebugEnabled(): return jsonify( {'Outline' : f'Placeholder outline for keyword {data["Keyword"]} with model: {data["Model"]}'} )  #type: ignore 
    return jsonify( {'Outline' : await GenerateOutline(data['Keyword'], data['SeachIntent'], data['Outlines'], data["Model"])} )           #type: ignore 

@g_.app.route('/outlinegen-generate-optimized-all', methods=['POST'])
async def outline_gen_generate_optimized_with_facts_all():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    query   = request.json['Query']   #type: ignore   

    intents  = [f'Search Intent placeholder for {kword["Keyword"]}' for kword in query]
    
    outlines = await gather(*[
       GenerateOptmizedOutlineWithFacts(kword["Keyword"], kword['Outlines'], intent, kword['SemanticAnalisys'], kword['Facts'], #type: ignore   
       kword['Tones'], kword['Audience'], kword["Model"], 
       request.json['Prompts'], request.json['SpecialInstructions'], dbug=IsDebugEnabled()) for kword, intent in zip(query, intents)])  #type: ignore     
   
    reply = [{'Keyword' : kword["Keyword"], 'Outline' : outline, 'SearchIntent': intent} for kword, outline, intent in zip(query, outlines, intents)]    
    return jsonify({'Reply' : reply})

async def outline_gen_generate_optimized_all():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    query   = request.json['Query']   #type: ignore   

    intents  = [f'Search Intent placeholder for {kword["Keyword"]}' for kword in query]
    #if False == IsDebugEnabled():
        #intents  =  await gather( *[GenSearchIntent('US', kword["Keyword"]) for kword in query] )

    #outlines = await gather(*[
       # GenerateOptmizedOutline(kword["Keyword"], kword['Outlines'], kword['SeachIntent'], kword['SemanticAnalisys'], kword['Tones'], kword['Audience'], dbug=IsDebugEnabled()) 
        #for kword in query]) 

    outlines = await gather(*[
       GenerateOptmizedOutline(kword["Keyword"], kword['Outlines'], intent, kword['SemanticAnalisys'], kword['Tones'], kword['Audience'], 
       kword["Model"], dbug=IsDebugEnabled()) for kword, intent in zip(query, intents)])   

    if query['Fix Outlines'] == True:                                                                                                   #type: ignore
        fixes    = await gather(*[OutlineFinalizeCeation({'Outline' : outline, 'Model' : query['Fix Model']}) for outline in outlines]) #type: ignore   
        outlines = [fix['Reply'] for fix in fixes]                                                                                  
   
    reply = [{'Keyword' : kword["Keyword"], 'Outline' : outline} for kword, outline, intent in zip(query, outlines, intents)]    
    return jsonify({'Reply' : reply});      

@g_.app.route('/outlinegen-generate-optimized', methods=['POST'])
async def outline_gen_generate_optimized_with_facts():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    data   = request.json

    outline = await GenerateOptmizedOutlineWithFacts(data["Keyword"], data['Outlines'], data['SeachIntent'], data['SemanticAnalisys'], data['Facts'], #type: ignore 
    data['Tones'], data['Audience'], data["Model"], request.json['Prompts'],  request.json['SpecialInstructions'], dbug=IsDebugEnabled())                        #type: ignore  

    if data['FixOutline'] == True:                                                                #type: ignore 
        fix     = await OutlineFinalizeCeation({'Outline' : outline, 'Model' : data['FixModel']}) #type: ignore
        outline = fix['Reply']                                                                    #type: ignore 
            
    return jsonify({'Outline' : outline})                                                         #type: ignore      
   

async def outline_gen_generate_optimized():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    data   = request.json
    print(data)   
        
    return jsonify({'Outline' : 
    await GenerateOptmizedOutline(data["Keyword"], data['Outlines'], data['SeachIntent'], data['SemanticAnalisys'], data['Tones'], data['Audience'], #type: ignore 
    data["Model"], dbug=IsDebugEnabled())}) #type: ignore          
  
#==================================================================================
#=============================CLUSTERCREATOR ROUTES================================
#================================================================================== 

@g_.app.route('/cluster_creator-gen-facts', methods=['POST'])
async def cluster_creator_gen_facts():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst   = request.json['Request']           #type: ignore
    if IsDebugEnabled(): return jsonify({'Reply' : f'Placeholder facts for kword {rqst["Keyword"]}'})
    facts  = await GenFacts(rqst['Keyword'], rqst['Model'], rqst['System'], rqst['User'])
    return jsonify({'Reply' : facts})

@g_.app.route('/cluster_creator-save', methods=['POST'])
async def cluster_creator_save():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst   = request.json['Request']           #type: ignore
    g_.db.WriteCluster(GetCurrentUserid(), rqst['Name'], dumps(rqst['Data']))
    return jsonify({'Reply' : ''})

@g_.app.route('/cluster_creator-load', methods=['POST'])
async def cluster_creator_load():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst   = request.json['Request']    #type: ignore 
    return jsonify({'Reply' : g_.db.LoadCluster(GetCurrentUserid(), rqst['Name'])})    

@g_.app.route('/cluster_creator-delete', methods=['POST'])
async def cluster_creator_delete():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst   = request.json['Request']    #type: ignore  
    g_.db.RemoveCluster(GetCurrentUserid(), rqst['Name'])
    return jsonify({'Reply' : ''})    

@g_.app.route('/cluster_creator-list', methods=['POST'])
async def cluster_creator_list():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    return jsonify({'Reply' : g_.db.ListClusters(GetCurrentUserid())})

@g_.app.route('/cluster_creator-entities', methods=['POST'])
async def cluster_creator_entities():
    if '' == GetCurrentUserid(): return await flask_templace('login') 
    print(request.json)    
    rqst    = request.json['Request'] #type: ignore 
    model   = request.json['Model']   #type: ignore 
    promtps = request.json['Prompts'] #type: ignore
    replys  = [
        {
            'Keyword'         : kword, 
            'CoreEntity'      : f'{kword} Placeholder Core Entity', 
            'ContextualFrame' : f'{kword} Placeholder Contextual Frame',
            'EntityAnalysis'  : f'{kword} Placeholder Entity Analysis'
        } 
        for kword in rqst] 
    if IsDebugEnabled(): return jsonify({'Reply' : replys})    
    replys     = await gather(*[GenerateEntities(kword, model, promtps) for kword in rqst])
    #analisyses = await gather(*[EntityAnalysis(reply['CoreEntity'], reply['ContextualFrame'], reply['Keyword']) for reply in replys])
    analisyses = await gather(*[EntityAnalysisOpenRouter(reply['CoreEntity'], reply['ContextualFrame'], reply['Keyword'], model, promtps) for reply in replys])
    #replys   = [reply | {'EntityAnalysis' : 'Placeholder Entity Analysis'} for reply in replys]
    replys   = [reply | {'EntityAnalysis' : analisys} for reply, analisys in zip(replys, analisyses)]
    return jsonify({'Reply' : replys})  

@g_.app.route('/cluster_creator-anchors', methods=['POST'])
async def cluster_creator_anchors():
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst   = request.json['Request'] #type: ignore
    #print(rqst) 
    replys = [
        {
            'Keyword' : kword['Keyword'], 
            'Anchors' : [f'{kword["Keyword"]} Placeholder anchor 1',  f'{kword["Keyword"]} Placeholder anchor 2']            
        } 
        for kword in rqst]
    if IsDebugEnabled(): return jsonify({'Reply' : replys})      
    #keywords_anchors = await gather(*[GenerateAnchors(kword['CoreEntity'], kword['Keyword'], kword['Anchors']) for kword in rqst])  
    keywords_anchors = await gather(*[GenerateAnchorsOpenRouter(kword['CoreEntity'], kword['Keyword'], kword['Model'], kword['Anchors']) for kword in rqst])  
    replys = [
        {
            'Keyword' : kword['Keyword'], 
            'Anchors' : anchors           
        } 
        for kword, anchors in zip(rqst, keywords_anchors)]   
    return jsonify({'Reply' : replys})   

@g_.app.route('/cluster_creator-zip-artciles', methods=['POST']) #type: ignore
async def cluster_creator_zip_artciles():    
    if '' == GetCurrentUserid(): return await flask_templace('login')     
    rqst   = request.json['Query'] #type: ignore

    from io import BytesIO
    from zipfile import ZipFile, ZIP_DEFLATED

    zip_buffer = BytesIO()

    with ZipFile(zip_buffer, "a", ZIP_DEFLATED, False) as zip_file:
        for article in rqst["Articles"]:
            zip_file.writestr(article['Name'] + '.txt', article['Content'])

    response = make_response(zip_buffer.getvalue())
    response.headers['Content-Type']        = 'application/octet-stream'
    response.headers['Content-Disposition'] = 'inline; filename=Articles'
    return response        

    with open(r'C:\Users\Peixoto\Documents\Freelance\streamlit_fix\Flask_Dashboard\flaskr\teste.zip', 'wb') as f:
        f.write(zip_buffer.getvalue())

    with open(r'C:\Users\Peixoto\Documents\Freelance\streamlit_fix\Flask_Dashboard\flaskr\teste.texr', 'w') as f: f.write('ok')  
    return 'ok' 

#==================================================================================
#=================================CONTENT CREATOR ROUTES===========================
#==================================================================================   
@g_.app.route('/content-creator_improve', methods=['POST'])   #type: ignore
async def content_creator_improve(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')    
    return await ImproveArticle(request.json)

@g_.app.route('/content-creator_titles-and-meta', methods=['POST'])   #type: ignore
async def content_creator_titles_and_meta(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')    
    return await GenTitlesAndMetadescription(request.json)
  
@g_.app.route('/content-creator_open_route', methods=['POST'])   #type: ignore
async def content_creator_open_route(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')   
    query    = request.json['Query']                            #type: ignore
    messages = query['Messages']
    section  = query['Section']
    _type    = query['Type']
    model    = query['Model']
    if IsDebugEnabled(): return jsonify({'Reply' : {'role': 'assistant', 'content' : f'Placeholder reply for section {section}'}}) 
    return jsonify({'Reply' : {'role': 'assistant', 'content' : await OpenRouterAChat(messages, model=model, temp=0.5)}})
    return jsonify({'Reply' : {'role': 'assistant', 'content' : RemoveTagsB(await OpenRouterAChat(messages, model=model, temp=0.5))}})

@g_.app.route('/content-creator_default-prompt', methods=['GET', 'POST'])   #type: ignore
async def content_creator_default_prompt(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')    
    return jsonify({'Reply' : CONTENT_GEN_DEFAULT, 'Legacy' : CONTENT_GEN_LEGACY})        

@g_.app.route('/content-creator_split-outline', methods=['POST'])   #type: ignore
async def content_creator_split_outline(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')
    query             = request.json['Query']                    #type: ignore
    merge_subsections = request.json['MergeSubsections']         #type: ignore    
    return jsonify({'Reply' : IpprovedOutlineSectionSpliter(query, merge_subsections)}) 

@g_.app.route('/content-creator_start', methods=['POST'])   #type: ignore 
async def content_creator_start(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')
    query             = request.json['Query']                      #type: ignore
    merge_subsections = request.json['Query']['MergeSubsections']  #type: ignore
    return jsonify({'Reply' : await StartChat(query, merge_subsections)})    

@g_.app.route('/content-creator_next', methods=['POST'])   #type: ignore 
async def content_creator_next(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')
    query = request.json['Query']                    #type: ignore
    return jsonify({'Reply' : await NextSextion(query)})   

#==================================================================================
#=================================INTERNAL LINKS ROUTES============================
#==================================================================================   

@g_.app.route('/internal_links-parse_csv', methods=['POST'])   #type: ignore 
async def internal_links_parse_csv(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')  
    if request is None: return err('Bad request')
    csv = request.json['CSV']                                  #type: ignore
    return jsonify({'Reply' : read_csv(StringIO(csv)).to_json(orient='records')})        

#==================================================================================
#=================================LINKS ROUTES=====================================
#==================================================================================     
@g_.app.route('/links_generate', methods=['POST'])
async def links_generate():    
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    query  = request.json['Query'] #type: ignore 
    reply  = {}
    signal = {}
    Thread(target=ClusterSimilarity, args=(query, signal, reply)).start() 
    while 'Done' not in signal.keys():await async_sleep(1)
    return jsonify({'Reply' : signal['Done']}) 
    return jsonify({'Reply' : ClusterSimilarity(query)}) 
    
   
def create_app():    
    g_.app.config['CSS']                     = 'static/css/'
    g_.app.config['AZIA']                    = 'static/azia/apps/static/assets/'
    g_.app.config['IMG']                     = 'static/img/'
    g_.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///seo_alchemy.db"   
    init_database(g_.app)
    import logging
    #log = logging.getLogger('werkzeug')
    #log.disabled = True
    log = logging.getLogger('werkzeug')
    #log.disabled = True
    #log.setLevel(logging.ERROR)
    return g_.app

if __name__ == '__main__': 
    import logging
    app = create_app()        
    log = logging.getLogger('werkzeug')
    log.disabled = True
    #log.setLevel(logging.ERROR)
    app.run() 
   
else: app = create_app()  