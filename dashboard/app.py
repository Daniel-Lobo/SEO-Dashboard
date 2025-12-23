from sys import flags, _getframe
from flask import Flask, render_template_string, jsonify, session, request
from flask_login import LoginManager, current_user
from flask_login.mixins import AnonymousUserMixin
from dashboard.database import Database
from os import listdir, getenv
from os.path import isfile, join, dirname, realpath
from aiofile import async_open
from dashboard.constants import ACCESS, STATUS
from os.path import dirname, realpath 
from json import dumps
from asyncio import coroutine
from types import CoroutineType  
from asyncio import sleep as async_sleep
from werkzeug.middleware.profiler import ProfilerMiddleware
from multiprocessing import Lock
from multiprocessing.managers import BaseManager, DictProxy, AcquirerProxy, BaseProxy #type: ignore
from copy import deepcopy
from threading import Thread
from asyncio import run
from random import randrange
from time import sleep
from multiprocessing import Process
from os import getpid
from datetime import datetime
from flask import request
from requests import post
from traceback import format_exc

def postlog(base_url, user, msg, msgtype = 'Log'):
    print("==================================================", base_url, user)
    if base_url == None or user == None: return
    url = f'{base_url}/log?user={user}&msgtype={msgtype}&password={g_.logpass}'
    print(url)
    post(url, json=msg)

class GlobalsSingleton():
    def __init__(self):        
        self.dir               = f'{dirname(realpath(__file__))}/'
        #self.db                = Database(self.dir, caller='GlobalsSingleton::__init__')
        self.app               = Flask(__name__, template_folder=f'{self.dir}HTML')
        #self.app.config['PROFILE'] = True
        #self.app.wsgi_app      = ProfilerMiddleware(self.app.wsgi_app, profile_dir="profiles")
        self.app.secret_key    = getenv("COOKIE_SECRET")
        self.colors            = {'theme' : {'strong' : '#6f42c1'}}
        self.auth              = LoginManager()          
        self.auth.init_app(self.app)   
        self.BlackList         = {'Articles' : [], 'Outlines' : [], 'Self References' : [], 'Stop Words' : []}
        self.debug             = False   
        self.Cache             = {'Pooled' : {}} 
        self.SettingsID        = 'cfaa70f0-5276-4c84-944b-beb4946b6ed0'
        self.DomainFilterID    = 'e070e1e7-6e19-49d7-985c-69755dac4cb9'
        self.TonesID           = 'ae9be87d-1d19-4328-95a2-5407ed77d09d'
        self.AudiencesID       = 'dc3da9b9-b017-44b4-a54c-d70853a29d6f'
        self.SharedDataID      = '1bdd2cb3-07a8-4a42-aff5-b1fed512b696'
        self.SharedBlackListID = 'f226ca57-33d6-4bd0-8218-029aca55f9c9'
        self.logpass           = '7cd7a42d-2f5b-4155-ba4a-b802987d1929'
        '''
        if False == self.db.IsUserEmail('admin@admin'): self.db.AddUser('admin', 'admin@admin', getenv('ADMIN_PASSWORD'))
        if False == self.db.IsUserEmail(self.SharedDataID): self.db.AddUser(self.SharedDataID, self.SharedDataID, getenv('ADMIN_PASSWORD'))
        if False == self.db.IsCluster(self.SharedDataID, self.SharedBlackListID):
            with open(dirname(realpath(__file__)) + '/resources/blacklisted_words.txt', 'r', encoding="utf-8") as f: 
                blacklist = [word.strip('\n').strip('\r').strip('\n').strip(' ') for word in f.read().splitlines()]
            data =  {'Articles Black List' : blacklist, 'Outlines Black List' : blacklist}    
            self.db.WriteCluster(self.SharedDataID, self.SharedBlackListID, dumps(data))
        self.db.SetUserAcessFlags('admin@admin', 0xffffffff)    
        '''    
        self.__content_creator_polled_data = {}
        
        self.manager = BaseManager(("127.0.0.1", 35791), b'c3db786-13e2-4e43-9003-478a6e3cabea')      
        sleep(float(randrange(1, 5)))  # prevents errors on startup
        try:            
            data = {}
            lock = Lock()
            self.manager.get_server()
            self.manager.register("Data", lambda: data, DictProxy)
            self.manager.register("GetLock", lambda: lock, AcquirerProxy)
            self.manager.start()                       
        except OSError:  # Address already in use                    
            self.manager.register("Data", None, DictProxy)
            self.manager.register("GetLock", None, AcquirerProxy)
            self.manager.connect()    

    def GetPooledData(self, user_id, data_id):        
        if user_id in self.__content_creator_polled_data:
            if data_id in self.__content_creator_polled_data[user_id]:
                return self.__content_creator_polled_data[user_id][data_id]

        return {}        

        user_data = {}
        self.manager.GetLock().acquire()                       #type: ignore
        try:
            data = self.manager.Data()                         #type: ignore
            if   user_id not in data.keys()                   : data[user_id] = {'Pooled' : {data_id : {}}}    
            elif data_id not in data[user_id]['Pooled'].keys(): 
                user_data = data[user_id]
                user_data['Pooled'][data_id] = {}
                data[user_id] = user_data    
            user_data = data[user_id]['Pooled'][data_id] 
        except Exception as e:
            print(e, format_exc())            
            pass   
        finally : 
            self.manager.GetLock().release()                  #type: ignore                
            return user_data       

    def SetPooledData(self, user_id, data_id=None, new_data=None):   
        #print("SetPooledData", user_id, data_id, new_data, self.__content_creator_polled_data.keys())
        if new_data == None: new_data = {}    
        if data_id  != None: 
            if user_id not in self.__content_creator_polled_data.keys(): self.__content_creator_polled_data[user_id] = {}
            self.__content_creator_polled_data[user_id][data_id] = new_data             
        return

        self.manager.GetLock().acquire()                                      #type: ignore
        try:
            if new_data is not None and data_id is not None: 
                copy                             = deepcopy(self.manager.Data())  #type: ignore
                copy[user_id]['Pooled'][data_id] = new_data                       #type: ignore
                data                             = self.manager.Data()            #type: ignore
                data[user_id]                    = copy[user_id]                  #type: ignore
            elif new_data is None and data_id is not None: 
                copy                             = deepcopy(self.manager.Data())  #type: ignore
                copy[user_id]['Pooled'][data_id] = {}                             #type: ignore
                data                             = self.manager.Data()            #type: ignore
                data[user_id]                    = copy[user_id]                  #type: ignore           
        except Exception as e:
            print(e, format_exc())
            pass   
        finally : 
            self.manager.GetLock().release()    
                                              #type: ignore
    def RemoveByBroadId(self, user_id, broad_id):
        if user_id in self.__content_creator_polled_data.keys():
            if broad_id in self.__content_creator_polled_data[user_id].keys():
                self.__content_creator_polled_data[user_id].pop(broad_id, None)
        print("RemoveByBroadId ", self.__content_creator_polled_data)        
        return        


        self.manager.GetLock().acquire()                                          #type: ignore
        try:
            copy = deepcopy(self.manager.Data())                                  #type: ignore
            if user_id  not in copy.keys()                   : return #self.manager.GetLock().release()  #type: ignore
            if broad_id not in copy[user_id]['Pooled'].keys(): return #self.manager.GetLock().release()  #type: ignore  
            to_remove = []
            for key, value in copy[user_id]['Pooled'].items():
                if value[broad_id] == key: to_remove.append(key)
            for k in to_remove:
                del copy[user_id]['Pooled'][k]
            print('Found ', len(to_remove), ' entries to remove')    
            data = self.manager.Data()                                            #type: ignore     
            data[user_id]['Pooled'] = copy[user_id]['Pooled']                     #type: ignore
        except Exception as e:
            print(e, format_exc())
            pass   
        finally : 
            self.manager.GetLock().release()                                      #type: ignore


class Pooled():
    def __init__(self, _id, task_lits: list) -> None:
        self.__base_url     = deepcopy(request.root_url)
        self.__Status       = STATUS.RUNNIG
        self.__tasks        = task_lits
        self.__CurrentTask  = task_lits[0]
        self.__index        = 0   
        self.__sleeptime    = 2.5
        self.__id           = _id
        self.__userid       = GetCurrentUserid()
        self.__dbug         = IsDebugEnabled()
        self.__broadid      = self.__class__.__name__
        self.__AddToPool()
        #print(self.__broadid)       
        print("Created pool ", self.__userid) 

    def IsDebugEnabled(self): return self.__dbug    
    def UserId(self)        : return self.__userid
    def BaseUrl(self)       : return self.__base_url 

    def __AddToPool(self):                
        user_data = g_.GetPooledData(self.__userid, self.__id)  
        #print(user_data)      
        if bool(user_data) == True:
            self.__Status = STATUS.NOT_POOLED                
            return             
        g_.SetPooledData(self.__userid, self.__id, self.serialize())    
        #print('Pooling ', self.__id)   
        #print('Pooling ', g_.GetPooledData(self.__userid, self.__id)  )     

    def __UpdatePool(self):           
        user_data = g_.GetPooledData(self.__userid, self.__id)      
        if bool(user_data) == False:                     
            raise Exception(f'Updating pool for id={self.__id }, but {self.__id } is not pooled')        
        g_.SetPooledData(self.__userid, self.__id, self.serialize())         

    async def Dummy(self)->str:
        #print('----')
        #await async_sleep(self.__sleeptime)  
        return ''  
    
    def GetStatus(self) -> str:
        return self.__Status 
    
    def GetTasks(self) -> list:
        return self.__tasks    
        
    def Finish(self, err: str) -> None:
        raise Exception(f'{self.__class__.__name__} does\'t reimplement Finish')
    
    def Fail(self, err: str) -> None:
        self.__Status = STATUS.FAILED
        self.Finish(err)

    def Finished(self) -> bool:
        return True if self.__Status == STATUS.FINISHED or self.__Status == STATUS.CANCELED or self.__Status == STATUS.FAILED else False    

    async def Next(self, task: CoroutineType)-> str:
        #postlog(self.__base_url, self.UserId, "Starting taks", msgtype='AI Request')    
        try:
            if self.__Status == STATUS.FINISHED:   raise Exception(f'{self.__class__.__name__} {STATUS.FINISHED}')
            if self.__Status == STATUS.CANCELED:   raise Exception(f'{self.__class__.__name__} {STATUS.CANCELED}')
            if self.__Status == STATUS.NOT_POOLED: raise Exception(f'{self.__class__.__name__} {STATUS.NOT_POOLED}')        
            if self.__index < len(self.__tasks): self.__CurrentTask = self.__tasks[self.__index]
            else                               : self.__Status = STATUS.FINISHED  
            self.__index += 1         
            err = await task
            if self.__index == len(self.__tasks): 
                self.Finish(err)
                self.__Status = STATUS.FINISHED

            self.__UpdatePool()
        except Exception as e:
            err = f'Error in {self.__class__.__name__} {self.__id} {self.__CurrentTask} {str(e)} {format_exc()}'
            #postlog(self.__base_url, self.UserId, err, msgtype='AI Request')    
        return err
    
    def cancel(self) -> None:
        self.__Status = STATUS.CANCELED
        
    def serialize(self) -> dict:        
        return {k.replace('_Pooled__', '').replace(f'_{self.__class__.__name__}__', ''): v for k, v in self.__dict__.items()}   

    async def Start(self, json: dict)-> None:    
        raise Exception(f'{self.__class__.__name__} does\'t reimplement Start')

    def __run(self, json: dict):
        run(self.Start(json))    

    def Run(self, json: dict):  
        Thread(target=self.__run, args=(json,)).start()


def IsFinished(data):
    return data['Status'] == STATUS.FINISHED        

g_ = GlobalsSingleton()  
def Pool(task_id, cleanup):     
    user_data = g_.GetPooledData(GetCurrentUserid(), task_id)
    #print(user_data)
    if bool(user_data) == False:            
        return jsonify({'Err' : f'{task_id} not pooled', 'Data' : {}})        
    if cleanup == 'true' and IsFinished(user_data): 
        #print("Cleaming UP", task_id)        
        g_.SetPooledData(GetCurrentUserid(), task_id, None)             
    return jsonify({'Err' : 'S_OK', 'Data' : user_data})

@g_.app.route('/pool', methods=['POST'])    #type: ignore 
def __Pool():    
    return Pool(request.args.get('id'), request.args.get('CleanUP'))  

@g_.app.route('/pool-remove-by-broad-id', methods=['POST'])    #type: ignore 
def PoolRemoveByBroadId():
    #print("/pool-remove-by-broad-id")
    g_.RemoveByBroadId(GetCurrentUserid(), request.args.get('id'))      
    return jsonify({'Err' : 'S_OK'})

def err(msg):
    return jsonify({'err' : f'{msg}'})

async def template(file):
    with open(f'{dirname(realpath(__file__))}/HTML/{file}.html', 'r') as f: return f.read()
    async with async_open(f'{dirname(realpath(__file__))}/HTML/{file}.html', 'r') as f: return await f.read()

async def flask_templace(file, **kargs):
    return render_template_string(await template(file), **kargs)

def GetCurrentUserid(): 
    return 'freeuser'
    return '' if isinstance(current_user, AnonymousUserMixin) else current_user.id

def IsAdmin():
    return True
    if ''    == GetCurrentUserid(): return False
    if False == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return False    
    return True

def SetDebugFlag(flag):
    if ''      == GetCurrentUserid(): return
    if False   == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return 
    access_flag = g_.db.GetUserByEmail(GetCurrentUserid())['access_flags']       
    if access_flag & ACCESS.DBUG: access_flag &= ~ACCESS.DBUG
    if flag == 'True': access_flag |= ACCESS.DBUG        
    g_.db.SetUserAcessFlags(GetCurrentUserid(), access_flag)

def IsDebugEnabled():
    #print( g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.DBUG )
    if ''    == GetCurrentUserid(): return False
    if False == g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.ADMIN: return False    
    if False != g_.db.GetUserByEmail(GetCurrentUserid())['access_flags'] & ACCESS.DBUG:  return True  
    return False 
