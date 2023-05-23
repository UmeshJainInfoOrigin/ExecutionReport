import pandas as pd
from sqlalchemy import create_engine,MetaData, Table, Column, Integer, String, text
import pymysql
import json
import os
from datetime import datetime

meta = MetaData()

#cucumberTestRunFile = 'results.json'
cucumberTestRunFile = 'CucumberRunnerTest.json'

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

def getFileModifiedTimeStamp(filePath):
    return datetime.fromtimestamp(os.path.getmtime(filePath)).strftime("%Y-%m-%d %H:%M:%S")

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
    dbConnection.execute(text(sqlInsert))
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
    #print(sqlNextVal)
    sqlEngine= get_connection(config)
    dbConnection= sqlEngine.connect()
    result = dbConnection.execute(text(sqlNextVal)).fetchone()
    dbConnection.close()
    #print('getNextVal', int(result[0]))
    #first row, first column
    return int(result[0])
    
def featureTable(executionData):
    clientId,sponsorId, applicationId,featureId,featureName = getAttribute(executionData, "description").split('~')
    uri = getAttribute(executionData, "uri").replace("\\","\\\\")
    description = getAttribute(executionData, "name")
    sqlSelectFeature=f"Select * from Feature where ApplicationId='{applicationId}' and FeatureId='{featureId}';"
    #print(sqlSelectFeature)
    result = executeSelect(sqlSelectFeature)
    if len(result.index) > 0:
        print('feature exists')
    else:
        if featureId == "??":
            featureId = 'F' + str(getNextVal('feature', 'featureid', 'F'))
        sqlInsertFeature = f"""Insert into {config['database']}.feature 
        (applicationId, featureid, FeatureName, description, uri, CreatedBy)
        values ('{applicationId}','{featureId}' ,'{featureName}','{description}','{uri}','infoOrigin');"""
        #print("feature not exists")
        #print (sqlInsertFeature)
        executeSqlInsert(sqlInsertFeature)
    return featureId

def featureExecutionTable(executionData,featureId):
    df = pd.json_normalize(executionData,record_path='elements')
    #startTime = df['start_timestamp'][0].replace('T',' ').replace('Z', ' ')
    #startTime = "2023-05-17 10:28"
    if 'start_timestamp' in df:
        startTime = df['start_timestamp'][0].replace('T',' ').replace('Z', ' ')
    else:
        startTime = getFileModifiedTimeStamp(os.getcwd() + '/' + cucumberTestRunFile)

    featureExecutionId = 'FE' + str(getNextVal('featureExecution', 'featureExecutionId', 'FE'))
    #featureId = 'F5'
    tcDuration=1
    totalScenario = df['steps'].count()
    sqlInsertFeatureExecution = f"""Insert into {config['database']}.featureexecution 
    (FeatureExecutionId, featureid, Duration, TotalScenario, StartTime, CreatedBy)
    values ('{featureExecutionId}','{featureId}' ,{tcDuration},{totalScenario},'{startTime}','infoOrigin');"""
    #print("feature not exists")
    #print (sqlInsertFeature)
    executeSqlInsert(sqlInsertFeatureExecution)
    return featureExecutionId

def scenarioTable(executionData,featureExecutionId):
    df = pd.json_normalize(executionData,record_path='elements')
    for index, scenarioName in enumerate(df['name'].tolist()):
        scenarioExecutionId = 'SE' + str(getNextVal('scenario', 'scenarioExecutionId', 'SE'))
        #featureId='F5'
        #featureExecutionId='FE1'
        scenarioId = df['tags'][index][0]['name'] if len(df['tags'][index])>0 else 'notags'
        description= df['description'][index]
        duration=1
        #print ('scenarioName', index, scenarioName, df['description'][index], df['tags'][index][0]['name'] if len(df['tags'][index])>0 else 'notags')       
        sqlInsertScenario = f"""Insert into {config['database']}.scenario 
        (ScenarioExecutionId, FeatureExecutionId, ScenarioId, ScenarioName, Description, Duration, CreatedBy)
        values ('{scenarioExecutionId}','{featureExecutionId}' ,'{scenarioId}','{scenarioName}','{description}',{duration},'infoOrigin');"""
        #print("feature not exists")
        #print (sqlInsertScenario)
        executeSqlInsert(sqlInsertScenario)
        dfScenarioSectionDF = df['steps'][index]
        scenarioStepTable(dfScenarioSectionDF,scenarioExecutionId,scenarioId)

def scenarioStepTable(dfScenarioSection,scenarioExecutionId,scenarioId):
    scenarioStatusFlag = True
    for stepDetail in dfScenarioSection:
        ScenarioStepExecutionId = 'SSE' + str(getNextVal('scenariostep', 'ScenarioStepExecutionId', 'SSE'))
        keyword = stepDetail['keyword'].strip()
        name = stepDetail['name']
        duration = round(stepDetail['result']['duration']/pow(10, 9),2)
        status = stepDetail['result']['status']
        if status.upper() != 'passed'.upper() and scenarioStatusFlag:
            scenarioStatusFlag = False
        sqlInsertScenarioStep = f"""Insert into {config['database']}.scenariostep 
                (ScenarioStepExecutionId,ScenarioExecutionId, ScenarioId, Keyword, Name, Duration, Status, CreatedBy)
            values ('{ScenarioStepExecutionId}','{scenarioExecutionId}' ,'{scenarioId}','{keyword}','{name}',{duration}, '{status}', 'infoOrigin')"""
        #print (sqlInsertScenarioStep)
        executeSqlInsert(sqlInsertScenarioStep)
    
    scenarioStatus ='passed' if scenarioStatusFlag else 'failed'
    sqlUpdateScenario = f"""update {config['database']}.scenario set status='{scenarioStatus}'
    where scenarioId='{scenarioId}' and ScenarioExecutionId='{scenarioExecutionId}';"""
    executeSqlInsert(sqlUpdateScenario)


if __name__ == '__main__':
    executionStartTime = datetime.now()

    executionData = json.load(open(cucumberTestRunFile))
    for featureFile in executionData:
        df = pd.json_normalize(featureFile,record_path='elements')
        featureId = featureTable(featureFile)
        featureExecutionId = featureExecutionTable(featureFile,featureId)
        scenarioTable(featureFile,featureExecutionId)
    
    sqlUpdateScenario = f"""UPDATE {config['database']}.scenario s
                    INNER JOIN (
                    SELECT ScenarioExecutionId, SUM(duration) as total
                    FROM test.scenarioStep
                    where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}'
                    GROUP BY ScenarioExecutionId
                    ) x ON s.ScenarioExecutionId = x.ScenarioExecutionId 
                    SET s.duration = x.total;"""
    executeSqlInsert(sqlUpdateScenario)
    #Update Failed number
    sqlUpdateFeatureExecution=f"""UPDATE {config['database']}.featureexecution FE
                    INNER JOIN (
                    SELECT FeatureExecutionId, count(*) as total
                    FROM test.scenario
                    where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}' and status='failed'
                    GROUP BY FeatureExecutionId
                    ) x ON FE.FeatureExecutionId = x.FeatureExecutionId 
                    SET FE.failed = x.total;"""
    executeSqlInsert(sqlUpdateFeatureExecution)
    #Update Passed number
    sqlUpdateFeatureExecution=f"""UPDATE {config['database']}.featureexecution FE
                    INNER JOIN (
                    SELECT FeatureExecutionId, count(*) as total
                    FROM test.scenario
                    where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}' and status='passed'
                    GROUP BY FeatureExecutionId
                    ) x ON FE.FeatureExecutionId = x.FeatureExecutionId 
                    SET FE.passed = x.total;"""
    executeSqlInsert(sqlUpdateFeatureExecution)

    executionEndTime = datetime.now()
    print('Total Execution Time=', executionEndTime - executionStartTime)
