import sqlite3
from sys import platform

class Database():
    def __init__(self, dir, caller='unspecified'):
        self.__path = f'{dir}dump.db' if platform == "win32" else f'{dir}../dump.db'
        self.__log: str = f'{caller} is opening {self.__path} databse\n' 
        print(f'{dir}dump.db')
        __db       = sqlite3.connect(self.__path).cursor()
        if not self.IsTable('users'):
            self.__log += 'User table does not exist on seo_toolset.db database, creating table\n'
            __db.execute("CREATE TABLE users(name, email, password, access_flags)")
            __db.connection.commit()
            if not self.IsTable('users'): self.__log += 'FATAL ERROR: user table could not be created on database\n'
            else                        : self.__log += 'user table created\n' 
        if not self.IsTable('clusters'):     
            self.__log += 'Clusters table does not exist on seo_toolset.db database, creating table\n'
            __db.execute("CREATE TABLE clusters(OwnerID, name, JSONData)")
            __db.connection.commit()
            if not self.IsTable('users'): self.__log += 'FATAL ERROR: clusters table could not be created on database\n'
            else                        : self.__log += 'user table created\n' 

    def __db(self):
        return sqlite3.connect(self.__path).cursor()

    def IsTable(self, table:str)->bool:
        tables = self.__db().execute('SELECT name FROM sqlite_master').fetchall()        
        if len(tables) == 0: return False 
        for tb in tables:
            if table in tb: return True
        return False        

    def IsUser(self, user):
        users = self.__db().execute('SELECT * FROM users WHERE name=?', (user,)).fetchall()           
        if len(users) == 0: return False        
        return user in users[0]      

    def IsUserEmail(self, email):
        users = self.__db().execute('SELECT * FROM users WHERE email=?', (email,)).fetchall()           
        if len(users) == 0: return False        
        return email in users[0]         

    def GetUser(self, user):
        users = self.__db().execute('SELECT * FROM users WHERE name=?', (user,)).fetchall()           
        if len(users) == 0: return False        
        return {'user_name' : users[0][0], 'email' :  users[0][1], 'password' : users[0][2], 'access_flags' : int(users[0][3])} 

    def GetUserByEmail(self, email):
        users = self.__db().execute('SELECT * FROM users WHERE email=?', (email,)).fetchall()           
        if len(users) == 0: return {'user_name' : 'not found', 'email' :  'not found', 'password' : 'not found', 'access_flags' : 0}          
        return {'user_name' : users[0][0], 'email' :  users[0][1], 'password' : users[0][2], 'access_flags' : int(users[0][3])}     

    def GetUsers(self):
        users = self.__db().execute('SELECT * FROM users').fetchall() 
        return [{'user_name' : user[0], 'email' :  user[1], 'password' : user[2], 'access_flags' : int(user[3])} for user in users]  

    def SetUserAcessFlags(self, email, flags):        
        if not self.IsUserEmail(email): return 'Not an user'
        db = self.__db()
        db.execute(f'UPDATE users SET access_flags={flags} WHERE email=?', (email,))
        db.connection.commit() 
        return f'Permissions for {email} updated'    

    def AddUser(self, name, email, password) ->str|None:        
        data = (name.strip(), email.strip(), password.strip(), 0) 
        cursor  = self.__db()
        cursor.execute("INSERT INTO users (name, email, password, access_flags) VALUES(?, ?, ?, ?);", data)
        cursor.connection.commit() 
        return None    
    
    def RemoveUser(self, user, email):
        if not self.IsUser(user): return 'Not an user'
        cursor  = self.__db()
        cursor.execute(f'DELETE FROM users WHERE name="{user}"')
        cursor.connection.commit() 
        return f'{user} deleted'

    def ListClusters(self, email):
        if not self.IsUserEmail(email): return 'Not an user'
        cursor   = self.__db()
        clusters = self.__db().execute('SELECT * FROM clusters WHERE OwnerID=?', (email,)).fetchall()           
        if len(clusters) == 0: return []       
        return [cluster[1] for cluster in clusters]

    def IsCluster(self, email, name):
        return True if name in self.ListClusters(email) else False

    def WriteCluster(self, email, name, data):  
        if not self.IsUserEmail(email): return 'Not an user' 
        cursor = self.__db()
        if self.IsCluster(email, name): cursor.execute(f'UPDATE clusters SET JSONData=? WHERE (OwnerID=? and name=?)', (data, email, name))
        else                          : cursor.execute(f'INSERT INTO clusters (OwnerID, name, JSONData) VALUES(?, ?, ?);', (email, name, data))  
        cursor.connection.commit()  

    def RemoveCluster(self, email, name):
        if not self.IsUserEmail(email): return 'Not an user' 
        cursor  = self.__db()
        cursor.execute(f'DELETE FROM clusters WHERE (OwnerID=? and name=?)', (email, name))
        cursor.connection.commit() 
        return f'{email} {name} deleted' 

    def LoadCluster(self, email, name):
        if not self.IsUserEmail(email)      : return {'err' : 'Not an user'}   
        if not self.IsCluster(email, name)  : return {'err' : f'Cluster {name} not found'}  
        clusters = self.__db().execute('SELECT * FROM clusters WHERE (OwnerID=? and name=?)', (email,name)).fetchall()           
        return clusters[0][2]
