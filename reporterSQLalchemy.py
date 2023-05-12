import pandas as pd
from sqlalchemy import create_engine,MetaData, Table, Column, Integer, String
import pymysql
import json

meta = MetaData()

feature = Table(
   'feature', meta, 
   Column('ApplicationId', String), 
   Column('FeatureId', String,primary_key = True), 
   Column('FeatureName', String), 
   Column('Description', String),
   Column('Uri', String), 
   Column('CreatedBy', String)
)

config = {
  'user': 'root',
  'password': 'MyNewPass',
  'host': '127.0.0.1',
  'database': 'test',
  'port' : 3306,
  'raise_on_warnings': True
}

def get_connection(config):
    return create_engine(
        url="mysql+pymysql://{0}:{1}@{2}:{3}/{4}".format(
            config['user'], config['password'], config['host'], config['port'], config['database']
        ),echo = False
    )

def executeSelect(sqlQuery):
    sqlEngine= get_connection(config)
    dbConnection= sqlEngine.connect()
    result= pd.read_sql(sqlQuery, dbConnection)
    pd.set_option('display.expand_frame_repr', False)
    dbConnection.close()
    #print('Total Rows', len(result.index))
    return result

def executeInsert():
    sqlEngine= get_connection(config)
    dbConnection= sqlEngine.connect()
    dbConnection.execute(feature.insert(),[
        {'ApplicationId':'A2', 'FeatureId':'F2', 'FeatureName':'Feature Name', 'Description':'Sample Desc', 'Uri':'complete path', 'CreatedBy': 'infoorigin'}
    ])
    dbConnection.commit()
    dbConnection.close()

def getAttribute(listItem, searchItem):
    for item in listItem:
        return item[searchItem]
    return "null"    
    
if __name__ == '__main__':
    try:
        executeInsert()
        sqlQuery= "select clientID, ClientName from client where clientId='C3'"
        print(executeSelect(sqlQuery))
        #df = pd.read_json('results.json')
        
        
# read the file
        data = json.load(open('results.json'))
        clientId,sponsorId, applicationId,featureId,featureName = getAttribute(data, "description").split('~')
        uri = getAttribute(data, "uri")
        sqlSelectFeature=f"Select * from Feature where ApplicationId='{applicationId}' and FeatureId='{featureId}'"
        result = executeSelect(sqlSelectFeature)
        if len(result.index) > 0:
            print('feature exists')
        else:
            sqlInsertFeature = f"""Insert into {config['database']}.feature 
            (applicationId, FeatureId,FeatureName, uri, CreatedBy)
            values ('{applicationId}', '{featureId}','{featureName}','{uri}','infoOrigin')"""
            print("feature not exists")
            print (sqlInsertFeature)
# load into pandas
        #df = pd.json_normalize(data,"elements")
        
        print('desc', )
        df = pd.json_normalize(data,record_path='elements')
        # df = (
        #         df["steps"]
        #         .apply(pd.Series)
        #         .merge(df, left_index=True, right_index = True)
        #     )
        
        for step in df['steps'].tolist():
            tcDuration = 0
            tcSteps = 0
            for stepDetail in step:
                tcDuration = tcDuration + stepDetail['result']['duration']/pow(10, 9)
                tcSteps = tcSteps + 1
            print('tc duration', tcDuration)
            print('tc steps', tcSteps)
        #print(df['steps'][0][0]['result']['duration'])
        #print(df['steps'][0][0]['line'])
    except Exception as ex:
        print("Connection could not be made due to the following error: \n", ex)