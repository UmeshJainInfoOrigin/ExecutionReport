import pandas as pd
from sqlalchemy import create_engine,MetaData, Table, Column, Integer, String, text
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

def executeSqlInsert(sqlInsert):
    sqlEngine= get_connection(config)
    dbConnection= sqlEngine.connect()
    print('sql insert successful', dbConnection.execute(text(sqlInsert)))
    dbConnection.commit()
    dbConnection.close()


def getAttribute(listItem, searchItem):
    #print('listItem', listItem[searchItem])
    # for item in listItem:
    #     print('return from here')
    #     return item[searchItem]
    #return "null~"    
    if listItem[searchItem] :
        return listItem[searchItem]

def getNextVal(tableName, colName, prefixChar):
    sqlNextVal = f""" (select mid({colName},length('{prefixChar}')+1)+1 from {tableName} order by CreatedON desc limit 1)
                union ( select 1 ) limit 1 ;"""
    print(sqlNextVal)
    sqlEngine= get_connection(config)
    dbConnection= sqlEngine.connect()
    result = dbConnection.execute(text(sqlNextVal)).fetchone()
    dbConnection.close()
    #print('getNextVal', int(result[0]))
    #first row, first column
    return int(result[0])
    
def featureTable(executionData):
    # Feature Table
    print('inside featurtable')
    print('desc', getAttribute(executionData, "description"))
    clientId,sponsorId, applicationId,featureId,featureName = getAttribute(executionData, "description").split('~')
    uri = getAttribute(executionData, "uri").replace("\\","\\\\")
    description = getAttribute(executionData, "name")
    sqlSelectFeature=f"Select * from Feature where ApplicationId='{applicationId}' and FeatureId='{featureId}'"
    print(sqlSelectFeature)
    result = executeSelect(sqlSelectFeature)
    if len(result.index) > 0:
        print('feature exists')
    else:
        if featureId == "??":
            featureId = 'F' + str(getNextVal('feature', 'featureid', 'F'))
        sqlInsertFeature = f"""Insert into {config['database']}.feature 
        (applicationId, featureid, FeatureName, description, uri, CreatedBy)
        values ('{applicationId}','{featureId}' ,'{featureName}','{description}','{uri}','infoOrigin')"""
        #print("feature not exists")
        print (sqlInsertFeature)
        executeSqlInsert(sqlInsertFeature)
    return featureId

def featureExecutionTable(executionData,featureId):
    df = pd.json_normalize(executionData,record_path='elements')
    #startTime = df['start_timestamp'][0].replace('T',' ').replace('Z', ' ')
    startTime = "2023-05-17 10:28"
    featureExecutionId = 'FE' + str(getNextVal('featureExecution', 'featureExecutionId', 'FE'))
    #featureId = 'F5'
    tcDuration=1
    totalScenario = df['steps'].count()
    sqlInsertFeatureExecution = f"""Insert into {config['database']}.featureexecution 
    (FeatureExecutionId, featureid, Duration, TotalScenario, StartTime, CreatedBy)
    values ('{featureExecutionId}','{featureId}' ,{tcDuration},{totalScenario},'{startTime}','infoOrigin')"""
    #print("feature not exists")
    #print (sqlInsertFeature)
    executeSqlInsert(sqlInsertFeatureExecution)
    return featureExecutionId
        

if __name__ == '__main__':
    
        #executeInsert()
        
    sqlQuery= "select clientID, ClientName from client where clientId='C3'"
    #print(executeSelect(sqlQuery))
    #df = pd.read_json('results.json')
    
    
# read the file
    executionData = json.load(open('results.json'))
    #print('featureId=', featureId)
    for featureFile in executionData:
        print('h')
        featureId = featureTable(featureFile)
        print('ii')
        featureExecutionId = featureExecutionTable(featureFile,featureId)

        #print('executionData', element)
    


# load into pandas
    #df = pd.json_normalize(data,"elements")
    
    #print('desc', )
        df = pd.json_normalize(featureFile,record_path='elements')
    # df = (
    #         df["steps"]
    #         .apply(pd.Series)
    #         .merge(df, left_index=True, right_index = True)
    #     )
    #print('duration=', df[df['steps']])
    # print('duration=', [pd.DataFrame(i)['result']['duration'].sum() 
    #                          for i in df['steps'].tolist()] )
    
    #m = df['steps'].explode()
    #df1= pd.DataFrame(m.tolist(),index=m.index)['result']
    #df2= pd.DataFrame(df1['duration'].tolist(),index=df1['duration'].index)
        
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
