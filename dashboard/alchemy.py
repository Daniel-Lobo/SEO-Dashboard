from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Column, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase
from json import dumps, loads
from sqlalchemy import select, delete, inspect, Text, BigInteger
from sqlalchemy.dialects.mysql import LONGTEXT as LongText, MEDIUMTEXT as MediumText
from datetime import datetime, timezone
from sys import _getframe 
from dashboard.app import g_, GetCurrentUserid, flask_templace
from flask import request, jsonify
from requests import post
from tempfile import gettempdir
from os.path import dirname, realpath
from sqlite3 import connect
from sys import argv
from os import getenv
from tempfile import gettempdir
from io import BytesIO
from os.path import isfile
from traceback import format_exc
from typing import cast

print('argv', argv)

def ReadDump(table):
    dir  = dirname(realpath(__file__)) + '/data'
    if not isfile(f'{dir}/dump.db'): dir = '/app/data/'
    path = f'{dir}/dump.db'
    db   = connect(path).cursor()
    return db.execute(f'SELECT * FROM {table}').fetchall()    

def ReadlAlchemyDump(table):
    dir  = dirname(realpath(__file__)) + '/data'
    if not isfile(f'{dir}/dump_alchemy.db'): dir = '/app/data/'
    path = f'{dir}/dump_alchemy.db'
    db   = connect(path).cursor()    
    return db.execute(f'SELECT * FROM {table}').fetchall()   

class Base(DeclarativeBase): pass
Alchemy_db = SQLAlchemy(model_class=Base)

class Settings(Alchemy_db.Model):    
    user_id:  Mapped[str] = mapped_column(String(64), primary_key=True)
    settings: Mapped[str] = mapped_column(LongText)


class SettingsProfiles(Alchemy_db.Model):
    profile   = Column(String(64), primary_key=True, unique=False)
    settings  = Column(LongText, unique=False)

class BlackLists(Alchemy_db.Model):    
    list_id       = Column(String(64), primary_key=True, unique=False)
    list_contents = Column(Text, unique=False)

class Logs(Alchemy_db.Model):  
    unique_id = Column(String(128), primary_key=True, unique=False)
    user      = Column(String(64), unique=False)
    _type     = Column(String(16), unique=False)
    timestamp = Column(Float, unique=False)
    function  = Column(String(16), unique=False)
    log       = Column(Text, unique=False)

class TonesAndAudiences(Alchemy_db.Model):
    unique_id = Column(String(64), primary_key=True, unique=False)
    data      = Column(MediumText, unique=False)     

class CTAS_B(Alchemy_db.Model):
    unique_id               = Column(String(128), primary_key=True, unique=False)
    CTA_client              = Column(Text, unique=False)    
    CTA_service_name        = Column(Text, unique=False)
    CTA_service_description = Column(Text, unique=False)

class CTA_SpecialInstructions(Alchemy_db.Model):
    unique_id               = Column(String(128), primary_key=True, unique=False)
    Intructions             = Column(Text, unique=False)    

class Users(Alchemy_db.Model):
    name         = Column(String(64), primary_key=True, unique=True)    
    email        = Column(String(64), unique=True) 
    password     = Column(String(64), unique=False) 
    access_flags = Column(BigInteger, unique=False) # access_flags

class ClustersB(Alchemy_db.Model):
    id        = Column(String(128), primary_key=True, unique=False)
    OwnerID   = Column(String(64), unique=False)
    name      = Column(String(16), unique=False)
    json      = Column(LongText, unique=False)   

class ClientOwnedClusters(Alchemy_db.Model):
    id          = Column(String(192), primary_key=True, unique=False)
    ClientID    = Column(String(64), unique=False)
    Domain      = Column(String(64), unique=False)    
    ClusterName = Column(String(32), unique=False)
    json        = Column(LongText, unique=False)


class DomainSettings(Alchemy_db.Model):
    id              = Column(String(128), primary_key=True, unique=False)
    Domain          = Column(String(64), unique=True)    
    Settings        = Column(MediumText, unique=False)
    AdditionalLinks = Column(MediumText, unique=False)


class AlchemySettingsProfiles:
    def __init__(self): 
        self.__session = Alchemy_db.session

    def SaveSettings(self, profile:str, settings:dict)->dict[str, str]: 
        # Creates of updates an entry returns an python exception of {"Err": "S_OK}
        try:
            if self.__session.execute(Alchemy_db.select(SettingsProfiles).where(
                SettingsProfiles.profile == profile)).first() == None:
                self.__session.execute(Alchemy_db.insert(SettingsProfiles).values(
                    profile = profile, settings = dumps(settings)))
            else: 
                self.__session.execute(Alchemy_db.update(SettingsProfiles).where(
                    SettingsProfiles.profile == profile).values(settings = dumps(settings)))
            self.__session.commit()            
            return {"Err": "S_OK"}
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')          

    def GetSettings(self, profile:str)->dict[str, str]: 
        try:
            settings = self.__session.execute(Alchemy_db.select(SettingsProfiles).where(
                SettingsProfiles.profile == profile)).first()
            if settings == None: return {"Err": "No settings", "Settings": loads('{}')}    
            return {"Err": "S_OK", "Settings": loads(settings[0].settings)}  #type: ignore
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')

    def DeleteSettings(self, profile:str)->dict[str, str]:
        try:
            self.__session.execute(Alchemy_db.delete(SettingsProfiles).where(
                SettingsProfiles.profile == profile)) 
            self.__session.commit()            
            return {"Err": "S_OK"}
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')

    def ListProfiles(self)->list[str]:
        return [profile[0] for profile in self.__session.execute(Alchemy_db.select(SettingsProfiles.profile)).fetchall()]        

class AlchemyClustersSettings:
    def __init__(self): 
        self.__session = Alchemy_db.session

    def DeleteDomain(self, domain:str)->dict[str, str]:
        try:
            self.__session.execute(Alchemy_db.delete(DomainSettings).where(
                DomainSettings.Domain == domain)) 
            self.__session.commit()            
            return {"Err": "S_OK"}
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')          

    def SaveSettings(self, domain:str, settings:dict)->dict[str, str]: 
        # Creates of updates an entry returns an python exception of {"Err": "S_OK}
        print("saving ", domain, settings)
        try:
            if self.__session.execute(Alchemy_db.select(DomainSettings).where(
                DomainSettings.Domain == domain)).first() == None:
                self.__session.execute(Alchemy_db.insert(DomainSettings).values(
                    Domain = domain, Settings = dumps(settings), AdditionalLinks = '[]', id = domain))
            else: 
                self.__session.execute(Alchemy_db.update(DomainSettings).where(
                DomainSettings.Domain == domain).values(Settings = dumps(settings)))
            self.__session.commit()            
            return {"Err": "S_OK"}
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')

    def GetSettings(self, domain:str)->dict[str, str]:
        try:
            settings = self.__session.execute(Alchemy_db.select(DomainSettings).where(
                DomainSettings.Domain == domain)).first()
            if settings == None: return {"Err": "S_OK", "Settings": loads('{}')}    
            return {"Err": "S_OK", "Settings": loads(settings[0].Settings)}  #type: ignore
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')

    def SaveAdditionalLinks(self, domain:str, links:dict)->dict[str, str]: 
        # Creates of updates an entry returns an python exception of {"Err": "S_OK}
        try:
            if self.__session.execute(Alchemy_db.select(DomainSettings).where(
                DomainSettings.Domain == domain)).first() == None:
                self.__session.execute(Alchemy_db.insert(DomainSettings).values(
                    Domain = domain, Settings = dumps({}), AdditionalLinks = dumps(links), id = domain))
            else: 
                self.__session.execute(Alchemy_db.update(DomainSettings).where(
                DomainSettings.Domain == domain).values(AdditionalLinks = dumps(links)))
            self.__session.commit()            
            return {"Err": "S_OK"}
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')

    def GetAdditionalLinks(self, domain:str)->dict[str, str]:
        try:
            settings = self.__session.execute(Alchemy_db.select(DomainSettings).where(
                DomainSettings.Domain == domain)).first()
            if settings == None: return {"Err": "S_OK", "AdditionalLinks": loads('{}')}       
            return {"Err": "S_OK", "AdditionalLinks": loads(settings[0].AdditionalLinks)}  #type: ignore
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')
                

class AlchemyClientOwnedClusters:    
    def __init__(self):
        self.__session = Alchemy_db.session

    def Save(self, client:str, domain:str, cluster_name:str, json:str)->dict[str, str]: 
        # Creates of updates an entry returns an python exception of {"Err": "S_OK}
        try:
            if self.IsCluster(client, domain, cluster_name):
                self.__session.execute(Alchemy_db.update(ClientOwnedClusters).where(
                    ClientOwnedClusters.ClientID    == client, 
                    ClientOwnedClusters.Domain      == domain, 
                    ClientOwnedClusters.ClusterName == cluster_name).values(json=json))
            else:    
                entry = ClientOwnedClusters(
                    id          = client + domain + cluster_name,  #type: ignore
                    ClientID    = client,        # type: ignore
                    Domain      = domain,        # type: ignore
                    ClusterName = cluster_name,  # type: ignore
                    json        = json,          # type: ignore
                )
                #print(entry.name)
                self.__session.add(entry)
            self.__session.commit()            
            return {"Err": "S_OK"}
        except Exception as e:
            return {"Err": str(e)}
         
    def DeleleClientDomain(self, client:str, domain:str)->dict[str, str]:
        try:
            self.__session.execute(Alchemy_db.delete(ClientOwnedClusters).where(
                ClientOwnedClusters.ClientID    == client, 
                ClientOwnedClusters.Domain      == domain))
            self.__session.commit()    
            return {"Err": "S_OK"}
        except Exception as e:
            return {"Err": str(e)}

    def DeleteClient(self, client:str)->dict[str, str]:
        try:
            self.__session.execute(Alchemy_db.delete(ClientOwnedClusters).where(
                ClientOwnedClusters.ClientID  == client))
            self.__session.commit()    
            return {"Err": "S_OK"}
        except Exception as e:
            return {"Err": str(e)}       

    def DeleteCluster(self, client:str, domain:str, cluster_name:str)->dict[str, str]:
        try:
            self.__session.execute(Alchemy_db.delete(ClientOwnedClusters).where(
                ClientOwnedClusters.ClientID    == client, 
                ClientOwnedClusters.Domain      == domain, 
                ClientOwnedClusters.ClusterName == cluster_name))    
            self.__session.commit()    
            return {"Err": "S_OK"}
        except Exception as e:
            return dict(Err = f'Error in {self.__class__.__name__} {str(e)} {format_exc()}')                        

    def IsCluster(self, client:str, domain:str, cluster_name:str)->bool:
        return self.__session.execute(Alchemy_db.select(ClientOwnedClusters).where(
            ClientOwnedClusters.ClientID    == client, 
            ClientOwnedClusters.Domain      == domain, 
            ClientOwnedClusters.ClusterName == cluster_name)).fetchone() is not None                

    def Load(self, client:str, domain:str, cluster_name:str)->str:    
        print(client, domain, cluster_name)
        try:
            return "S_OK", self.__session.execute(Alchemy_db.select(ClientOwnedClusters).where(
                ClientOwnedClusters.ClientID    == client, 
                ClientOwnedClusters.Domain      == domain, 
                ClientOwnedClusters.ClusterName == cluster_name)).fetchone()[0].json            #type: ignore
        except Exception as e:
            return "Err", str(e)  #type: ignore

    def ListClients(self):
        clients = self.__session.execute(Alchemy_db.select(ClientOwnedClusters.ClientID).distinct()).fetchall()
        return [client[0] for client in clients]

    def ListDomains(self, client: str)->list[str]:
        domains = self.__session.execute(Alchemy_db.select(ClientOwnedClusters.Domain).where(
            ClientOwnedClusters.ClientID == client).distinct()).fetchall()
        return [domain[0] for domain in domains if domain[0] != "PLACEHOLDER"]

    def ListClusters(self, client: str, domain: str)->list[str]:
        clusters = self.__session.execute(Alchemy_db.select(ClientOwnedClusters.ClusterName).where(
            ClientOwnedClusters.ClientID    == client, 
            ClientOwnedClusters.Domain      == domain)).fetchall()
        return [cluster[0] for cluster in clusters if cluster[0] != "PLACEHOLDER"]    
       
    def GetDomainClusters(self, client: str, domain: str, clusters_list: list[str])->list[str]:
        try:
            clusters = self.__session.execute(Alchemy_db.select(ClientOwnedClusters).where(
                ClientOwnedClusters.ClientID    == client, 
                ClientOwnedClusters.Domain      == domain)).fetchall()
            return [{"Name" : cluster[0].ClusterName, "Json": loads(cluster[0].json)} for cluster in clusters if cluster[0].ClusterName in clusters_list]      #type: ignore
        except Exception as e:
            print("Exception", e, format_exc())
            return []     

    def Delete(self, client: str, domain: str, cluster_name: str):
        try:
            self.__session.execute(Alchemy_db.delete(ClientOwnedClusters).where(
                ClientOwnedClusters.ClientID    == client, 
                ClientOwnedClusters.Domain      == domain, 
                ClientOwnedClusters.ClusterName == cluster_name))
            self.__session.commit()    
            return {"Err": "S_OK"}
        except Exception as e:
            return {"Err": str(e)}   

class AlchemyCTASIntructions:
    def __init__(self):
        self.__session = Alchemy_db.session

    def InsertodModify(self, unique_id:str, instructions:str)->str:
        try:
            if self.__session.execute(Alchemy_db.select(CTA_SpecialInstructions).where(
                CTA_SpecialInstructions.unique_id == unique_id)).first() is None:
                entry = CTA_SpecialInstructions(
                    unique_id   = unique_id,  # type: ignore
                    Intructions = instructions # type: ignore
                )
                self.__session.add(entry)   
            else:
                self.__session.execute(Alchemy_db.update(CTA_SpecialInstructions).where(
                    CTA_SpecialInstructions.unique_id == unique_id).values(Intructions=instructions))
            self.__session.commit()    
            return 'S_OK'
        except Exception as e:
            return f'Error in {self.__class__.__name__} {str(e)} {format_exc()}'

    def Get(self, unique_id:str)->str:
        try:
            instructions = self.__session.execute(Alchemy_db.select(CTA_SpecialInstructions).where(
                CTA_SpecialInstructions.unique_id == unique_id)).first()
            if instructions is None: return ''
            return instructions[0].Intructions  #type: ignore
        except Exception as e:
            return f'Error in {self.__class__.__name__} {str(e)} {format_exc()}'       

class AlchemyCTAS:
    def __init__(self):
        self.__session = Alchemy_db.session

    def Import(self):
        ctas = ReadlAlchemyDump('ctas_b')
        for cta in ctas:           
            self.AddService({'Client' : cta[1], 'ServiceName' : cta[2], 'ServiceDescription' : cta[3]})

        print("LISTING CTAS")
        for client in self.ListClients():
            print(client)
            for service in self.ListServices(client):
                print('\t', service)   
        print("FINISHED")        

    def IsService(self, client, service_name, service_description)->bool:
        service = self.__session.execute(Alchemy_db.select(CTAS_B).where(
            CTAS_B.CTA_client              == client, 
            CTAS_B.CTA_service_name        == service_name, 
            CTAS_B.CTA_service_description == service_description)).fetchone()
        print("=====================================++",service)
        return False if service is None else True      

    def IsServiceByName(self, client, service_name)->bool:
        service = self.__session.execute(Alchemy_db.select(CTAS_B).where(
            CTAS_B.CTA_client              == client, 
            CTAS_B.CTA_service_name        == service_name)).fetchone()
        print("=====================================++",service)
        return False if service is None else True 

    def AddService(self, request)->str:
        if 'Client' not in request or 'ServiceName' not in request or 'ServiceDescription' not in request:
            return 'BAD_REQUEST'
        if self.IsService(request['Client'], request['ServiceName'], request['ServiceDescription']): 
            return f'Client {request["Client"]} already has service {request["ServiceName"]}\n{request["ServiceDescription"]}'    
        CTA = CTAS_B(
            unique_id               = request['Client'] + request['ServiceName'],  #type: ignore
            CTA_client              = request['Client'],             #type: ignore
            CTA_service_name        = request['ServiceName'],        #type: ignore
            CTA_service_description = request['ServiceDescription']  #type: ignore
        )                 
        self.__session.add(CTA)
        self.__session.commit()   
        return 'S_OK'
    
    def AddServiceInstructions(self, client, service_name, instructions)->str:
        if self.IsServiceByName(client, service_name) == False:
            return f'Client {client} does not have service {service_name}'
        try:
            if self.__session.execute(Alchemy_db.select(CTA_SpecialInstructions).where(
                CTA_SpecialInstructions.unique_id == client + service_name)).first() is None:
                entry = CTA_SpecialInstructions(
                    unique_id   = client + service_name,  # type: ignore
                    Intructions = instructions            # type: ignore
                )
                self.__session.add(entry)
            else:
                self.__session.execute(Alchemy_db.update(CTA_SpecialInstructions).where(
                    CTA_SpecialInstructions.unique_id == client + service_name).values(Intructions=instructions))
            self.__session.commit()    
            return 'S_OK'
        except Exception as e:
            return f'Error in {self.__class__.__name__} {str(e)} {format_exc()}'

    def GetServiceInstructions(self, client, service_name)->str:
        try:
            instructions = self.__session.execute(Alchemy_db.select(CTA_SpecialInstructions).where(
                CTA_SpecialInstructions.unique_id == client + service_name)).first()
            if instructions is None: return ''
            return instructions[0].Intructions  #type: ignore
        except Exception as e:
            return f'Error in {self.__class__.__name__} {str(e)} {format_exc()}'

    def DeleteService(self, client, service_name, service_description):             #type: ignore
        CTA = self.__session.execute(Alchemy_db.select(CTAS_B).where(
            CTAS.CTA_client == client,                                              #type: ignore
            CTAS.CTA_service_name == service_name,                                  #type: ignore
            CTAS.CTA_service_description == service_description)).fetchone()        #type: ignore
        self.__session.delete(CTA)
        self.__session.commit()
        return 'S_OK'
    
    def ListClients(self) -> list[str]:
        clients = self.__session.execute(Alchemy_db.select(CTAS_B.CTA_client).distinct()).fetchall()
        if clients == []: return []
        clients = [client[0] for client in clients]
        return clients

    def ListServices(self, client) -> list[str]:
        services = self.__session.execute(Alchemy_db.select(CTAS_B.CTA_service_name).where(CTAS_B.CTA_client == client)).fetchall()        
        if services == []: return []
        services = [service[0] for service in services]
        return services

    def GetServiceDescription(self, client, service_name) -> str:
        desc = self.__session.execute(Alchemy_db.select(CTAS_B.CTA_service_description).where(
            CTAS_B.CTA_client == client, 
            CTAS_B.CTA_service_name == service_name)).fetchone()
        #print(desc)
        return desc[0] if desc else ''

    def UpdateServiceDescription(self, client, service_name, service_description):
        CTA = self.__session.execute(Alchemy_db.update(CTAS_B).where(
            CTAS_B.CTA_client == client, 
            CTAS_B.CTA_service_name == service_name).values(CTA_service_description=service_description))       
        self.__session.commit()
        return 'S_OK'

    def DeleteClient(self, client):
        self.__session.execute(Alchemy_db.delete(CTAS_B).where(CTAS_B.CTA_client == client))    
        self.__session.commit()

    def DeleteService(self, client, service_name):
        self.__session.execute(Alchemy_db.delete(CTAS_B).where(CTAS_B.CTA_client == client, CTAS_B.CTA_service_name == service_name))
        self.__session.commit()        
        

class AlchemyTonesAndAudiences:
    __data_imported__ = False
    def __init__(self):
        self.__session = Alchemy_db.session   
        
    def Import(self):
        if AlchemyTonesAndAudiences.__data_imported__: return self
        dump_data = ReadlAlchemyDump("tones_and_audiences")[0][1]
        dump_data = loads(dump_data)
        for tone in dump_data['Tones']        : self.AppendTone(tone)
        for audience in dump_data['Audiences']: self.AppendAudience(audience)

        data = self.Get()
        print("LISTING TONES")
        for tone in data['Tones']: 
            print('\ttone: ' + tone['Name'], 'Desc:', "...", "Tag:", tone['Tag'])
        print("FINISHED LISTING TONES")
        print("LISTING AUDIENCES")
        for audience in data['Audiences']: 
            print('\taudience: ' + audience['Name'], 'Desc:', "...", "Tag:", audience['Tag'])
        print("FINISHED LISTING AUDIENCES")    
        AlchemyTonesAndAudiences.__data_imported__ = True
        return self
   
    def __Get(self):
        v = self.__session.execute(Alchemy_db.select(TonesAndAudiences.data)).fetchall()           
        if v == []:
            tones = TonesAndAudiences(
                unique_id  = 'TonesAndAudiences', # type: ignore
                data       = '{"Tones": [], "Audiences": []}'                   # type: ignore
            )
            self.__session.add(tones)
            self.__session.commit()
            return self.__session.execute(Alchemy_db.select(TonesAndAudiences.data)).fetchall()[0][0]     
        return v[0][0]    

    def Get(self):
        return loads(self.__Get())     

    def AppendTone(self, tone:dict)->str:
        try:    
            if 'Name' not in tone.keys() or 'Description' not in tone.keys() or 'Tag' not in tone.keys(): return "Bad object"
            v = self.Get()
            for t in v['Tones']:
                if t['Name'] == tone['Name'] and t['Description'] == tone['Description'] and t['Tag'] == tone['Tag']:
                    return 'Already exists'
            v['Tones'].append(tone)
            self.__session.execute(Alchemy_db.update(TonesAndAudiences).where(TonesAndAudiences.unique_id == 'TonesAndAudiences').values(data=dumps(v)))
            self.__session.commit()
            return 'S_OK'
        except Exception as e: return str(e)    

    def AppendAudience(self, aud:dict)->str:
        try:
            if 'Name' not in aud.keys() or 'Description' not in aud.keys() or 'Tag' not in aud.keys(): return "Bad object"
            v = self.Get()
            for a in v['Audiences']:
                if a['Name'] == aud['Name'] and a['Description'] == aud['Description'] and a['Tag'] == aud['Tag']:
                    return 'Already exists'
            v['Audiences'].append(aud)
            self.__session.execute(Alchemy_db.update(TonesAndAudiences).where(TonesAndAudiences.unique_id == 'TonesAndAudiences').values(data=dumps(v)))
            self.__session.commit()
            return 'S_OK'
        except Exception as e: return str(e)   

    def DeleteTone(self, tone:str)->str:
        try:
            if "Name" not in tone or "Description" not in tone or "Tag" not in tone: return "Bad object"
            v      = self.Get()
            edited = []
            for t in v['Tones']:
                if t['Name'] == tone['Name'] and t['Description'] == tone['Description'] and t['Tag'] == tone['Tag']: continue  #type: ignore
                edited.append(t)
            v['Tones'] = edited
            self.__session.execute(Alchemy_db.update(TonesAndAudiences).where(TonesAndAudiences.unique_id == 'TonesAndAudiences').values(data=dumps(v)))
            self.__session.commit()
            return 'S_OK'
        except Exception as e: return str(e)

    def DeleteAudience(self, aud:str)->str:
        try:
            if "Name" not in aud or "Description" not in aud or "Tag" not in aud: return "Bad object"
            v      = self.Get()
            edited = []             
            for a in v['Audiences']:
                if a['Name'] == aud['Name'] and a['Description'] == aud['Description'] and a['Tag'] == aud['Tag']: continue  #type: ignore
                edited.append(a)
            v['Audiences'] = edited
            self.__session.execute(Alchemy_db.update(TonesAndAudiences).where(TonesAndAudiences.unique_id == 'TonesAndAudiences').values(data=dumps(v)))
            self.__session.commit()
            return 'S_OK'
        except Exception as e: return str(e)    


class AlchemySetings:
    def __init__(self):
        self.__session = Alchemy_db.session

    def IsRegistered(self, user: str) -> bool:
        settings = self.__session.execute(Alchemy_db.select(Settings).where(Settings.user_id == user)).fetchall()
        return False if len(settings) == 0 else True

    def RegisterUser(self, user: str) -> None:    
        entry = Settings(
            user_id  = user,   # type: ignore
            settings = '{}'    # type: ignore
        )
        self.__session.add(entry)
        self.__session.commit()

    def InitUser(self, user: str, settings: dict) -> None:    
        if self.IsRegistered(user) == False:  self.RegisterUser(user)
        self.__session.execute(Alchemy_db.update(Settings).where(Settings.user_id == user).values(settings=dumps(settings)))
        self.__session.commit()

    def Get(self, user: str) -> dict:
        if self.IsRegistered(user) == False:
            self.RegisterUser(user)
            return {}
        s = select(Settings).where(Settings.user_id == user)      
        settings = loads(self.__session.scalars(s).all()[0].settings)
        if isinstance(settings, str): settings = loads(settings)        
        return settings

    def Set(self, user, key, value):
        current      = self.Get(user)    
        current[key] = value
        self.__session.execute(Alchemy_db.update(Settings).where(Settings.user_id == user).values(settings=dumps(current)))
        self.__session.commit()

    def SetAll(self, user, json:object):
        current = self.Get(user)  
        #print("==============================================")
        #print(current.keys())
        #print(json.keys())
        self.__session.execute(Alchemy_db.update(Settings).where(Settings.user_id == user).values(settings=dumps(json)))
        self.__session.commit()    

    def List(self):
        settings = self.__session.scalars(select(Settings)).all()
        return [{'user_id' : i.user_id, 'settings' : loads(i.settings)} for i in settings]

    def Summary(self):    
        settings = self.__session.scalars(select(Settings)).all()
        return [{'user_id' : i.user_id, 'settings' : len(loads(i.settings))} for i in settings]

class AlchemyLogs:

    def __init__(self):
        self.__session = Alchemy_db.session

    def log(self, user, msg: str, log_type: str = 'Log'):
        entry = Logs(
            unique_id = user + str(datetime.now(timezone.utc).timestamp()),  # type: ignore
            user      = user,                                                # type: ignore
            timestamp = datetime.now(timezone.utc).timestamp(),              # type: ignore
            function  = _getframe(1).f_code.co_name,                         # type: ignore
            log       = msg,                                                 # type: ignore
            _type     = log_type                                             # type: ignore
        )
        self.__session.add(entry)
        self.__session.commit()    

    def GetKeys(self):    
        users     = [r.user     for r in self.__session.query(Logs.user).distinct()]    
        functions = [r.function for r in self.__session.query(Logs.function).distinct()]    
        _types    = [r._type    for r in self.__session.query(Logs._type).distinct()]            
        return {'Users' : users, 'Functions' : functions, 'Types' : _types}

    def DeleteLog(self, user: str, function: str, time: float):
        #print(user, function, time)
        Logs.query.where(Logs.user == user).where(Logs.function == function).where(Logs.timestamp == time).delete()      
        self.__session.commit()    
    
    def GetLogs(self, user: str, functions: list[str], types: list[str])-> list[dict] :
        #print(functions, types)
        s = select(Logs).where(Logs.user == user).where(Logs.function.in_(functions)).where(Logs._type.in_(types)).order_by(Logs.timestamp)   
        s = self.__session.scalars(s).all()        
        return [{
            'Timestamp'    : datetime.fromtimestamp(float(str(r.timestamp))).strftime('%d/%m/%Y, %H:%M:%S'),
            'Time'         : str(r.timestamp),
            'Function'     : r.function,
            'Log'          : r.log,
            'Type'         : r._type 
        } for r in s]


class AlchemyUsers:
    __users_imported__ = False
    def __init__(self):                
        self.__session = Alchemy_db.session                  

    def Import(self):   
        if AlchemyUsers.__users_imported__ == True: return self
        dump_data      = ReadDump('users')
        print('LISTING USERS')
        for user in dump_data: print(user)
        print('FINISHED')
        for user in dump_data:
            if not self.IsUser(user[0]): self.AddUser(user[0], user[1], user[2], user[3])    
        AlchemyUsers.__users_imported__ = True   
        return self

    def AddUser(self, name, email, password, acess_flags=0) ->None:        
        #print(name, email, password, acess_flags)
        entry = Users(
            name         = name,     # type: ignore
            email        = email,    # type: ignore
            password     = password,  # type: ignore
            access_flags = acess_flags  #type: ignore
        )
        self.__session.add(entry)
        self.__session.commit()
        return 'S_OK'  #type: ignore

    def GetUser(self, name)->dict|None:
        user = self.__session.execute(Alchemy_db.select(Users).where(Users.name == name)).fetchall()   
        if user == []: return None
        return {'user_name' : user[0][0].name, 'email' :  user[0][0].email, 'password' : user[0][0].password, 'access_flags' : int(user[0][0].access_flags)}  

    def GetUserByEmail(self, email)->dict:
        user = self.__session.execute(Alchemy_db.select(Users).where(Users.email == email)).fetchall()   
        if user == []: return {'user_name' : 'not found', 'email' :  'not found', 'password' : 'not found', 'access_flags' : 0}  
        return {'user_name' : user[0][0].name, 'email' :  user[0][0].email, 'password' : user[0][0].password, 'access_flags' : int(user[0][0].access_flags)}    

    def GetUsers(self)->list[dict]:
        users = self.__session.execute(Alchemy_db.select(Users)).fetchall()        
        return [{'user_name': user[0].name, 'email': user[0].email, 'password': user[0].password, 'access_flags': int(user[0].access_flags)} for user in users]

    def IsUser(self, name)->bool: 
        user = self.__session.execute(Alchemy_db.select(Users).where(Users.name == name)).fetchall()
        return False if user == [] else True

    def IsUserEmail(self, email)->bool:
        user = self.__session.execute(Alchemy_db.select(Users).where(Users.email == email)).fetchall()
        return False if user == [] else True    

    def RemoveUser(self, user, email)->str: 
        if not self.IsUser(user): return 'Not an user'
        self.__session.execute(Alchemy_db.delete(Users).where(Users.name == user).where(Users.email == email))
        self.__session.commit()
        return f'{user} deleted'

    def SetUserAcessFlags(self, user, flags):
        self.__session.execute(Alchemy_db.update(Users).where(Users.email == user).values(access_flags=flags))
        self.__session.commit()  

class AlchemyBlackLists:
    __keys = ['Articles Black List', 'Outlines Black List','Self References Black List', 'Stop Words']    
    def __init__(self):
        self.__session = Alchemy_db.session     

    def Import(self):
        clusters = ReadDump('clusters')          
        for cluster in clusters:
            if cluster[1] == g_.SharedBlackListID and cluster[0] == g_.SharedDataID:
                lists = loads(cluster[2])
                #print(lists.keys())
                
        for key in AlchemyBlackLists.__keys:
            if key in lists:                #type: ignore
                self.Set(key, lists[key])   #type: ignore 

        print("ENUMERATING BLACK LISTS")
        for key in AlchemyBlackLists.__keys:
            if key in lists:                #type: ignore
                print(self.Get(key))
        print("FINISHED")    

    def Get(self, list_id)->list:
        b_list = self.__session.execute(Alchemy_db.select(BlackLists).where(BlackLists.list_id == list_id)).fetchall()           
        if len(b_list) == 0: return []
        return loads(b_list[0][0].list_contents)

    def Set(self, list_id, list_contents:list):
        if self.Get(list_id) == []:   
            list_item = BlackLists(
                list_id       = list_id,                #type: ignore
                list_contents = dumps(list_contents)    #type: ignore
            )  
            self.__session.add(list_item)
            self.__session.commit()
            return
        self.__session.execute(Alchemy_db.update(BlackLists).where(BlackLists.list_id == list_id).values(list_contents=dumps(list_contents)))  
        self.__session.commit()  

    def GetAll(self)->dict: 
        ret = {}
        for key in AlchemyBlackLists.__keys: ret[key] = self.Get(key)
        return ret

    def SetAll(self, lists:dict):
        for key in lists.keys(): self.Set(key, lists[key])    

class AlchemyClusters:
    __clusters_imported__ = False
    def __init__(self):
        self.__session = Alchemy_db.session

    def Import(self):
        AlchemyClusters.__clusters_imported__ = True
        #if getenv('CLOUDRON_MYSQL_URL', None) == None: AlchemyClusters.__clusters_imported__ = True
        if AlchemyClusters.__clusters_imported__ == True: return self
        users    = AlchemyUsers().Import()
        settings = AlchemySetings()
        tones    = AlchemyTonesAndAudiences().Import()
        
        self.__session = Alchemy_db.session
        dump_data      = ReadDump('clusters')
        
        meta_clusters_ids = {g_.TonesID : "Tones", g_.AudiencesID : 'Audiences', g_.SharedBlackListID : 'BlackList', g_.logpass : 'Logpass',
        g_.SettingsID : 'Settings', g_.DomainFilterID : 'Domain Filter'}        
        for cluster in dump_data: 
            who  = cluster[0]
            what = cluster[1]
            if who == g_.SharedDataID: who = 'SharedData'
            for _id in meta_clusters_ids.keys():
                if what == _id: what = meta_clusters_ids[_id]     

            if cluster[1] == g_.SettingsID:
                settings.InitUser(cluster[0], cluster[2])         

            #if cluster[1] == g_.SharedBlackListID and cluster[0] == g_.SharedDataID:
                #print(who, cluster[2])                              

            elif cluster[1] not in meta_clusters_ids.keys() and cluster[0] != g_.SharedDataID: 
                user = users.GetUserByEmail(who)   
                if user is not None:
                    self.WriteCluster(user['email'], cluster[1], cluster[2])
            #print(who, what)           
          
        print('LISTING CLUSTERS')
        for user in users.GetUsers():
            print('\tUser:', user['user_name'])
            print('\t', self.ListClusters(user['email']))
        print('FINISHED')     

        print("LISTING SETTINGS")
        for user in settings.Summary():
            print('\tUser:', user['user_id'], 'Settings lenght:', user['settings'])
        print("FINISHED")   

        AlchemyBlackLists().Import()
        AlchemyCTAS().Import()
        AlchemyClusters.__clusters_imported__ = True
        return self

    def IsCluster(self, email, name)->bool:        
        clusters = self.__session.execute(Alchemy_db.select(ClustersB).where(ClustersB.name == name).where(ClustersB.OwnerID == email)).fetchall()
        return False if clusters == [] else True      

    def WriteCluster(self, email, name, json)->str:
        if not AlchemyUsers().IsUserEmail(email): return 'Not an user'
        if self.IsCluster(email, name):
            self.__session.execute(Alchemy_db.update(ClustersB).where(ClustersB.name == name).where(ClustersB.OwnerID == email).values(json=json))
        else:    
            entry = ClustersB(
                id        = email + name,  # type: ignore
                OwnerID   = email,         # type: ignore
                name      = name,          # type: ignore
                json      = json,          # type: ignore
            )
            #print(entry.name)
            self.__session.add(entry)
            self.__session.commit()
        return 'S_OK'

    def ListClusters(self, email)->list[str]:
        clusters = self.__session.execute(Alchemy_db.select(ClustersB).where(ClustersB.OwnerID == email)).fetchall()
        return [cluster[0].name for cluster in clusters]       

    def LoadCluster(self, email, name)->str|dict:
        if not AlchemyUsers().IsUserEmail(email): return {'err' : 'Not an user'}    
        if not self.IsCluster(email, name):       return {'err' : f'Cluster {name} not found'}    
        clusters = self.__session.execute(Alchemy_db.select(ClustersB).where(ClustersB.name == name).where(ClustersB.OwnerID == email)).fetchall()   
        return clusters[0][0].json    

class UsersAndClusters():
    def AddUser(self, name, email, password, acess_flags=0) ->None: return AlchemyUsers().AddUser(name, email, password, acess_flags)
    def GetUser(self, name)->dict|None                            : return AlchemyUsers().GetUser(name)  
    def GetUserByEmail(self, email)->dict                         : return AlchemyUsers().GetUserByEmail(email)
    def GetUsers(self)->list[dict]                                : return AlchemyUsers().GetUsers()      
    def IsUser(self, name)->bool                                  : return AlchemyUsers().IsUser(name)
    def IsUserEmail(self, email)->bool                            : return AlchemyUsers().IsUserEmail(email)
    def RemoveUser(self, user, email)->str                        : return AlchemyUsers().RemoveUser(user, email)
    def SetUserAcessFlags(self, user, flags)                      : return AlchemyUsers().SetUserAcessFlags(user, flags)
    def IsCluster(self, email, name)->bool                        : return AlchemyClusters().IsCluster(email, name)
    def WriteCluster(self, email, name, json)->str                : return AlchemyClusters().WriteCluster(email, name, json)
    def ListClusters(self, email)->list[str]                      : return AlchemyClusters().ListClusters(email)
    def LoadCluster(self, email, name)->str|dict                  : return AlchemyClusters().LoadCluster(email, name)

def init_database(app):
    #app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{gettempdir()}/alchemy.db'
    #app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://daniel:lobo@localhost:3000/seo_dashboard'
    _URL       =  getenv('CLOUDRON_MYSQL_URL', None)         
    _USERNAME  =  getenv('CLOUDRON_MYSQL_USERNAME', None)     
    _PASSWORD  =  getenv('CLOUDRON_MYSQL_PASSWORD', None)     
    _HOST      =  getenv('CLOUDRON_MYSQL_HOST', None)         
    _PORT      =  getenv('CLOUDRON_MYSQL_PORT', None)         
    _DATABASE  =  getenv('CLOUDRON_MYSQL_DATABASE', None)
    print('url', _URL)
    print('username', _USERNAME)
    print('password', _PASSWORD)
    print('host', _HOST)
    print('port', _PORT)
    print('database', _DATABASE)
    dump_command = \
    f'mysqldump -h${_HOST} -u${_USERNAME} -p${_PASSWORD} --single-transaction --routines --triggers --no-tablespaces ${_DATABASE} > /tmp/mysqldump.sql'
    print(dump_command)
    mysql =  f'mysql://{_USERNAME}:{_PASSWORD}@172.18.30.1:{_PORT}/{_DATABASE}' 
    print('mysql', mysql)
    if _URL is not None: app.config['SQLALCHEMY_DATABASE_URI'] = mysql        
    #else: app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{dirname(realpath(__file__))}/seo_dashboard.db'
    else: app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://root:pocoto@localhost:3306/seo_dashboard'
    Alchemy_db.init_app(app)
    #return
    with app.app_context(): 
        Alchemy_db.create_all()        
        print("========================")
        '''
        users = UsersAndClusters()
        #print(users.GetUser("daniel"))
        #print(users.GetUser("vilebaldo"))
        #print(users.GetUserByEmail("dl.lobo@hotmail.com"))
        for user in g_.db.GetUsers():
            if not users.IsUser(user['user_name']):
                users.AddUser(user['user_name'], user['email'], user['password'], user['access_flags'])    
            for cluster in g_.db.ListClusters( user['email']):
                json = g_.db.LoadCluster(user['email'], cluster)
                #print("old",user['user_name'], cluster, loads(json).keys())   
                if not users.IsCluster(user['email'], cluster):
                    users.WriteCluster(user['email'], cluster, json)
                json = users.LoadCluster(user['email'], cluster)
                #print("new",user['user_name'], cluster, loads(json).keys())            
            #print(user)            
        #print(users.GetUsers())
        #users.RemoveUser('daniel', 'dl.lobo@hotmail.com') 
        #print(users.GetUsers())
        '''        
        #AlchemyClusters()
        #return   
        #           
        g_.db = UsersAndClusters()     #type: ignore
        #print(g_.db.ListClusters('dl.lobo@hotmail.com'))   
        if False == g_.db.IsUserEmail('admin@admin'): g_.db.AddUser('admin', 'admin@admin', getenv('ADMIN_PASSWORD'))               #type: ignore
        if False == g_.db.IsUserEmail(g_.SharedDataID): g_.db.AddUser(g_.SharedDataID, g_.SharedDataID, getenv('ADMIN_PASSWORD'))   #type: ignore
        if False == g_.db.IsCluster(g_.SharedDataID, g_.SharedBlackListID):                                                         #type: ignore                
            with open(dirname(realpath(__file__)) + '/resources/blacklisted_words.txt', 'r', encoding="utf-8") as f: 
                blacklist = [word.strip('\n').strip('\r').strip('\n').strip(' ') for word in f.read().splitlines()]
            data =  {'Articles Black List' : blacklist, 'Outlines Black List' : blacklist}    
            #g_.db.WriteCluster(g_.SharedDataID, g_.SharedBlackListID, dumps(data))
        g_.db.SetUserAcessFlags('admin@admin', 0xffffffff)                                                                          #type: ignore
        AlchemyClusters().Import() 
    return
    with app.app_context(): 
        #print(inspect(Alchemy_db.engine).get_table_names() )
        #print(Logs.__table__.name)
        tables = inspect(Alchemy_db.engine).get_table_names() 
        for table in [Settings, Logs]:
            if table.__table__.name not in tables:                
                Alchemy_db.create_all([table.__table__])    
                

@g_.app.route('/Settings-Profiles/save', methods=['POST'])
async def settings_profiles_save():
    try:
        if '' == GetCurrentUserid(): return await render_template('login') #type: ignore
        
        rqst = request.json
        if not rqst:
            return jsonify({"Err": "Missing request body"}), 400
            
        profile  = request.args.get('profile')
        settings = rqst  # Use the entire request body as settings
        
        if not profile:
            return jsonify({"Err": "Missing profile parameter"}), 400
            
        settings_profiles = AlchemySettingsProfiles()
        result            = settings_profiles.SaveSettings(profile, settings)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"Err": f"Error: {str(e)}"}), 500

@g_.app.route('/Settings-Profiles/get', methods=['POST'])
async def settings_profiles_get():
    try:
        if '' == GetCurrentUserid(): return await render_template('login') #type: ignore
        
                  
        profile = request.args.get('profile')        
        if not profile:
            return jsonify({"Err": "Missing profile parameter"}), 400
            
        settings_profiles = AlchemySettingsProfiles()
        result            = settings_profiles.GetSettings(profile)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"Err": f"Error: {str(e)}"}), 500

@g_.app.route('/Settings-Profiles/delete', methods=['POST'])
async def settings_profiles_delete():
    try:
        if '' == GetCurrentUserid(): return await render_template('login') #type: ignore
                  
        profile = request.args.get('profile')        
        if not profile:
            return jsonify({"Err": "Missing profile parameter"}), 400
            
        settings_profiles = AlchemySettingsProfiles()
        result            = settings_profiles.DeleteSettings(profile)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"Err": f"Error: {str(e)}"}), 500

@g_.app.route('/Settings-Profiles/list', methods=['POST'])
async def settings_profiles_list():
    try:
        if '' == GetCurrentUserid(): return await render_template('login') #type: ignore
        
        settings_profiles = AlchemySettingsProfiles()
        result            = settings_profiles.ListProfiles()
        
        return jsonify({"Err": "S_OK", "Profiles": result})
    except Exception as e:
        return jsonify({"Err": f"Error: {str(e)}"}), 500                    

@g_.app.route('/domain-settings_get-settings', methods=['GET', 'POST'])
async def get_settings():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    domain = request.args.get('Domain')
    alchemy_clusters_settings = AlchemyClustersSettings()
    return jsonify(alchemy_clusters_settings.GetSettings(domain))        #type: ignore

@g_.app.route('/domain-settings-save-settigs', methods=['POST'])
async def save_settings():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    rqst     = request.json
    domain   = rqst['Domain']    #type: ignore
    settings = rqst['Settings']  #type: ignore
    alchemy_clusters_settings = AlchemyClustersSettings()
    return jsonify(alchemy_clusters_settings.SaveSettings(domain, settings))

@g_.app.route('/domain-settings-get-additional-links', methods=['POST'])
async def get_additional_links():
    if '' == GetCurrentUserid(): return await render_template('login')    #type: ignore
    domain = request.args.get('Domain')
    alchemy_clusters_settings = AlchemyClustersSettings()
    return jsonify(alchemy_clusters_settings.GetAdditionalLinks(domain))  #type: ignore

@g_.app.route('/domain-settings-save-additional-links', methods=['POST'])
async def save_additional_links():
    if '' == GetCurrentUserid(): return await render_template('login')    #type: ignore
    rqst   = request.json
    domain = rqst['Domain']  #type: ignore
    links  = rqst['Links']   #type: ignore
    alchemy_clusters_settings = AlchemyClustersSettings()
    return jsonify(alchemy_clusters_settings.SaveAdditionalLinks(domain, links))  

@g_.app.route('/client_owned_clusters-delete-client', methods=['GET', "POST"])    #type: ignore
async def delete_client():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    client = request.args.get('Client')
    if not client:
        return jsonify({'Err': 'Missing required fields'}), 400
    client_domains = AlchemyClientOwnedClusters().ListDomains(cast(str, client))    
    for domain in client_domains:
        err = AlchemyClustersSettings().DeleteDomain(cast(str, domain))
        if err["Err"] != 'S_OK': 
            return jsonify(dict(Err = f"Failed to delete domain {domain} {err['Err']}"))
    return jsonify(AlchemyClientOwnedClusters().DeleteClient(cast(str, client)))

@g_.app.route('/client_owned_clusters-delete-client-domain', methods=['POST']) #type: ignore
async def delete_client_domain():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    client = request.args.get('Client')
    domain = request.args.get('Domain')
    if not all([client, domain]):
        return jsonify({'Err': 'Missing required fields'}), 400
    err = AlchemyClientOwnedClusters().DeleleClientDomain(cast(str, client), cast(str, domain))
    if err["Err"] == 'S_OK': err = AlchemyClustersSettings().DeleteDomain(cast(str, domain))    
    print(err)  
    return jsonify(err)         

@g_.app.route('/client_owned_clusters-delete-cluster', methods=['POST']) #type: ignore
async def delete_client_cluster():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    client       = request.args.get('Client')
    domain       = request.args.get('Domain')
    cluster_name = request.args.get('ClusterName')
    if not all([client, domain, cluster_name]):
        return jsonify({'Err': 'Missing required fields'}), 400
    return jsonify(AlchemyClientOwnedClusters().DeleteCluster(client, domain, cluster_name))   #type: ignore     

@g_.app.route('/client_owned_clusters-is_cluster', methods=['POST'])
async def is_client_owned_cluster():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    client       = request.args.get('Client')
    domain       = request.args.get('Domain')
    cluster_name = request.args.get('ClusterName')
    if not all([client, domain, cluster_name]):
        return jsonify({'Reply': 'Missing required fields'}), 400
    alchemy_client_owned_clusters = AlchemyClientOwnedClusters()
    return jsonify( {"Reply" : alchemy_client_owned_clusters.IsCluster(client, domain, cluster_name)} )  #type: ignore

@g_.app.route('/client_owned_clusters-delete', methods=['POST'])
async def delete_client_owned_cluster():
    if '' == GetCurrentUserid(): return await render_template('login')     #type: ignore
    client       = request.args.get('Client')
    domain       = request.args.get('Domain')
    cluster_name = request.args.get('ClusterName')
    if not all([client, domain, cluster_name]):
        return jsonify({'Err': 'Missing required fields'}), 400
    alchemy_client_owned_clusters = AlchemyClientOwnedClusters()
    return jsonify( alchemy_client_owned_clusters.Delete(client, domain, cluster_name) )  #type: ignore

@g_.app.route('/client_owned_clusters-save', methods=['POST'])
async def save_client_owned_cluster():
    if '' == GetCurrentUserid(): return await render_template('login')  #type: ignore
    rqst         = request.json['Request']                              #type: ignore    
    client       = rqst['Client']
    domain       = rqst['Domain']
    cluster_name = rqst['ClusterName']
    json         = dumps(rqst['data'])
    #print(type(rqst['data']))

    #print("dumped json" , json)

    if not all([client, domain, cluster_name, json]):
        return jsonify({'Err': 'Missing required fields'}), 400

    alchemy_client_owned_clusters = AlchemyClientOwnedClusters()
    return jsonify( alchemy_client_owned_clusters.Save(client, domain, cluster_name, json) )   

@g_.app.route('/client_owned_clusters-list_clients', methods=['POST'])
async def list_clients():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    alchemy_client_owned_clusters = AlchemyClientOwnedClusters()
    clients                       = alchemy_client_owned_clusters.ListClients()
    print(clients)
    return jsonify({'Clients': clients}), 200

@g_.app.route('/client_owned_clusters-list_domains', methods=['POST'])
async def list_domains():
    if '' == GetCurrentUserid(): return await render_template('login')   #type: ignore
    client                        = request.args.get('client')
    alchemy_client_owned_clusters = AlchemyClientOwnedClusters()
    domains                       = alchemy_client_owned_clusters.ListDomains(client)  #type: ignore
    return jsonify({'Domains': domains}), 200

@g_.app.route('/client_owned_clusters-list_clusters', methods=['POST'])
async def list_clusters():
    if '' == GetCurrentUserid(): return await render_template('login')  #type: ignore
    client                        = request.args.get('client')
    domain                        = request.args.get('domain')
    alchemy_client_owned_clusters = AlchemyClientOwnedClusters()
    clusters                      = alchemy_client_owned_clusters.ListClusters(client, domain)  #type: ignore
    return jsonify({'Clusters': clusters}), 200

@g_.app.route('/client_owned_clusters-load', methods=['POST'])
async def load_cluster():
    if '' == GetCurrentUserid(): return await render_template('login')  #type: ignore
    alchemy_client_owned_clusters = AlchemyClientOwnedClusters()
    client                        = request.args.get('client')
    domain                        = request.args.get('domain')
    cluster_name                  = request.args.get('cluster')
    result                        = alchemy_client_owned_clusters.Load(client, domain, cluster_name)  #type: ignore
    #print(result[1])
    if result[0] == 'S_OK':
        cluster = loads(result[1])
        cluster["Additional Keywords"] = []
        return jsonify({'Cluster': cluster}), 200
    else:
        return jsonify({'Err': result[1]}), 500

def GetKeyWordURL(keyword, cluster):
    url = keyword["BaseURL"]
    if url == '': url = cluster["Json"]["KEYWORDS_BaseURL"] 
    while url.endswith('\\') or url.endswith('/'):  url = url[:-1]  
    return url
    
@g_.app.route('/client_owned_clusters_get-domain-clusters', methods=['GET', 'POST'])
async def GetAnchors():
    if '' == GetCurrentUserid(): return await flask_templace('login')
    client                        = request.args.get('Client')
    domain                        = request.args.get('Domain')
    clusters                      = request.json['Clusters']                   #type: ignore
    anchors                       = []
    clusters = AlchemyClientOwnedClusters().GetDomainClusters(client, domain, clusters)  #type: ignore
    for cluster in clusters:
        for kword in cluster['Json']["Keywords"]:  #type: ignore
            anchors.append({
                "Domain"     : domain,                                                   #type: ignore
                "Cluster"    : cluster['Name'],                                          #type: ignore
                "Keyword"    : kword["Keyword"],                                         #type: ignore
                "Anchors"    : kword["Anchors"],                                         #type: ignore
                "Url"        : GetKeyWordURL(kword, cluster),                            #type: ignore
                "CoreEntity" : kword["Core Entity"],                                     #type: ignore
                "DontAppendKword" : kword["DontAppendKword"] if 'DontAppendKword' in kword else False,  #type: ignore                  
            })     
    return jsonify({'Reply' : anchors})     

@g_.app.route('/client_owned_clusters_edit-cluster-anchors', methods=['GET', 'POST'])       
async def EditClusterAnchors():
    if '' == GetCurrentUserid(): return await flask_templace('login')
    client      = request.args.get('Client')
    domain      = request.args.get('Domain')   
    clusters    = request.json['Clusters']  #type: ignore
    #try:
    for cluster_name, new_data in clusters.items():
        err, cluster_content = AlchemyClientOwnedClusters().Load(client, domain, cluster_name)  #type: ignore
        cluster_content      = loads(cluster_content)
        if err != 'S_OK': continue
        for cluster in new_data:
            keyword = cluster['Keyword']
            anchors = cluster['Anchors']
            for index, kword in enumerate(cluster_content["Keywords"]):
                if cluster_content["Keywords"][index]["Keyword"] == keyword:
                    print("Editing================================", anchors)
                    cluster_content["Keywords"][index]["Anchors"] = anchors
        print(AlchemyClientOwnedClusters().Save(client, domain, cluster_name, dumps(cluster_content)))  #type: ignore
    return jsonify({'Reply' : 'S_OK'})    
    #except Exception as e: return jsonify({'Reply' : str(e)})

@g_.app.route('/client=owned-clusters_update-cluster-settings', methods=['GET', 'POST']) #type: ignore
async def UpdateClusterSettings():
    if '' == GetCurrentUserid(): return await flask_templace('login')
    client       = request.args.get('Client')
    domain       = request.args.get('Domain')
    cluster_name = request.args.get('ClusterName')
    if not all([client, domain, cluster_name]):
        return jsonify({'Err': 'Missing required fields (Client, Domain or ClusterName)'}), 400
    if request.json is None:
        return jsonify({'Err': 'Missing required fields (json)'}), 400
    if "Settings" not in request.json:
        return jsonify({'Err': 'Missing required fields (Settings)'}), 400
    settings     = request.json['Settings'] #type: ignore
    cluster      = AlchemyClientOwnedClusters().Load(client, domain, cluster_name)  #type: ignore
    if cluster[0] != 'S_OK': 
        return jsonify({'Err' : "Failed to load cluster: " + cluster}), 500
    cluster      = loads(cluster[1])
    cluster['CLUSTER-SETTINGS-V2'] = settings
    return jsonify(AlchemyClientOwnedClusters().Save(client, domain, cluster_name, dumps(cluster)))  #type: ignore
      

@g_.app.route('/CTAs-delete-client', methods=['GET', 'POST'])
async def CTA_DeleteClient():    
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    return jsonify({'Reply' : AlchemyCTAS().DeleteClient(request.json['Client'])})  #type: ignore

@g_.app.route('/CTAs-delete-service', methods=['GET', 'POST'])
async def CTA_DeleteService():
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    return jsonify({'Reply' : AlchemyCTAS().DeleteService(request.json['Client'], request.json['ServiceName'])})  #type: ignore

@g_.app.route('/CTAs-update-description', methods=['GET', 'POST'])
async def CTA_UpdateDescription():
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    return jsonify({'Reply' : AlchemyCTAS().UpdateServiceDescription(request.json['Client'], request.json['ServiceName'], request.json['ServiceDescription'])})  #type: ignore

@g_.app.route('/CTAs-get-service-description', methods=['GET', 'POST'])
async def CTA_GetServiceDescription():
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    return jsonify({'Reply' : AlchemyCTAS().GetServiceDescription(request.json['Client'], request.json['ServiceName'])})  #type: ignore

@g_.app.route('/CTAs-list-clients', methods=['GET', 'POST'])
async def CTAListClients():
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    return jsonify({'Clients' :AlchemyCTAS().ListClients()})

@g_.app.route('/CTAs-list-services', methods=['GET', 'POST'])
async def CTAListServices():
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    return jsonify({'Services' :AlchemyCTAS().ListServices(request.json['Client'])})    #type: ignore 

@g_.app.route('/CTAs-add-service', methods=['GET', 'POST'])
async def CTAAddService():
    if '' == GetCurrentUserid(): 
        #print('login')
        return await flask_templace('login')    
    return jsonify({'Reply' : AlchemyCTAS().AddService(request.json)})

@g_.app.route('/get-tones-and-audiences-new-api', methods=['GET', 'POST'])
async def GetTonesAndAudiencesNewApi():
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    v = AlchemyTonesAndAudiences().Get()  
    #print(v)
    return jsonify(v)

@g_.app.route('/append-tone-new-api', methods=['GET', 'POST'])
async def AppendToneNewApi():
    if '' == GetCurrentUserid(): return await flask_templace('login')
    return jsonify({'Reply' : AlchemyTonesAndAudiences().AppendTone(request.json)})      #type: ignore

@g_.app.route('/append-audience-new-api', methods=['GET', 'POST'])
async def AppendAudienceNewApi():
    if '' == GetCurrentUserid(): return await flask_templace('login')
    return jsonify({'Reply' : AlchemyTonesAndAudiences().AppendAudience(request.json)})    #type: ignore

@g_.app.route('/delete-tone-new-api', methods=['GET', 'POST'])
async def DeleteToneNewApi():
    if '' == GetCurrentUserid(): return await flask_templace('login')    
    return jsonify({'Reply' : AlchemyTonesAndAudiences().DeleteTone(request.json)})  #type: ignore

@g_.app.route('/delete-audience-new-api', methods=['GET', 'POST'])
async def DeleteAudienceNewApi():   
    if '' == GetCurrentUserid(): return await flask_templace('login')
    return jsonify({'Reply' : AlchemyTonesAndAudiences().DeleteAudience(request.json)})   #type: ignore       

@g_.app.route('/get-global-settings-new-api', methods=['GET', 'POST'])
async def GetGlobalSettingsNewApi():
    if '' == GetCurrentUserid(): return await flask_templace('login')
    settings = AlchemySetings().Get(g_.SharedDataID)
    print(type(settings))
    return jsonify({'Settings' : settings})    

@g_.app.route('/global-settings-new-api-set-value', methods=['GET', 'POST'])
async def GlobalSettingSetValue(): 
    if '' == GetCurrentUserid(): return await flask_templace('login')
    try: 
        AlchemySetings().Set(g_.SharedDataID, request.json['Key'], request.json['Value']) # type: ignore
        return jsonify({'Reply' : 'S_OK'})
    except Exception as e: return jsonify({'Reply' : str(e)})

@g_.app.route('/global-settings-new-api-set-all-values', methods=['GET', 'POST'])
async def GlobalSettingSetAllValues(): 
    #print("==========================================================")
    if '' == GetCurrentUserid(): return await flask_templace('login')
    #try: 
    AlchemySetings().SetAll(g_.SharedDataID, request.json['Request']['Data'])  #type: ignore
    return jsonify({'Reply' : 'S_OK'})
    #except Exception as e: return jsonify({'Reply' : str(e)})    

@g_.app.route('/log', methods=['POST'])
def logroute():
    return jsonify({})
    password = request.args.get('password')
    if password != g_.logpass: return jsonify({})    
    user    = request.args.get('user')
    msgtype = request.args.get('msgtype')    
    settings = g_.db.LoadCluster(user, "cfaa70f0-5276-4c84-944b-beb4946b6ed0")
    if settings == None: return jsonify({})
    if not isinstance(settings, dict): settings = loads(settings) #type: ignore  
    if 'AI Logs Enabled' not in settings.keys(): return jsonify({})
    if settings['AI Logs Enabled'] == False: return jsonify({})
    AlchemyLogs().log(user, str(request.json), str(msgtype))     
    return c

def postlog(base_url, user, msg, msgtype = 'Log'):
    return
    print("==================================================", base_url, user)
    if base_url == None or user == None: return
    url = f'{base_url}/log?user={user}&msgtype={msgtype}&password={g_.logpass}'
    print(url)
    post(url, json=msg)


@g_.app.route("/import-database", methods=['POST']) #type: ignore   
def import_database():               
    with open(gettempdir() + '/dump.db', "wb") as f: f.write(request.get_data())  
    AlchemyUsers().Import()
    AlchemyTonesAndAudiences().Import()
    AlchemyClusters().Import()    
    return jsonify({'Err': 'S_OK'})    

@g_.app.route("/import-alchemy-database", methods=['POST']) #type: ignore   
def import_alchemy_database():             
    with open(gettempdir() + '/dump_alchemy.db', "wb") as f: f.write(request.get_data())      
    AlchemyUsers().Import()
    AlchemyTonesAndAudiences().Import()
    AlchemyClusters().Import()
    return jsonify({'Err': 'S_OK'})      

@g_.app.route('/CTAs-add-service-instructions', methods=['GET', 'POST'])
async def CTAAddServiceInstructions():    
    if '' == GetCurrentUserid(): return await flask_templace('login')
    try:
        data = request.json
        if not data:
            return jsonify({'Reply': 'Missing request body'}), 400
            
        client       = data.get('Client')
        service_name = data.get('ServiceName')        
        instructions = data.get('Instructions')
        
        if not all([client, service_name, instructions]):
            return jsonify({'Reply': 'Missing required fields: Client, ServiceName, Description, Instructions'}), 400
            
        result = AlchemyCTAS().AddServiceInstructions(client, service_name, instructions)
        return jsonify({'Reply': result})
    except Exception as e:
        return jsonify({'Reply': f'Error: {str(e)}'}), 500

@g_.app.route('/CTAs-get-service-instructions', methods=['GET', 'POST'])
async def CTAGetServiceInstructions():
    if '' == GetCurrentUserid(): return await flask_templace('login')
    try:
        data = request.json
        if not data:
            return jsonify({'Reply': 'Missing request body'}), 400

        client       = data.get('Client')
        service_name = data.get('ServiceName')
        
        if not all([client, service_name]):
            return jsonify({'Reply': 'Missing required parameters: Client, ServiceName'}), 400
            
        instructions = AlchemyCTAS().GetServiceInstructions(client, service_name)
        return jsonify({'Reply': 'S_OK', 'Instructions': instructions})
    except Exception as e:
        return jsonify({'Reply': f'Error: {str(e)}'}), 500
