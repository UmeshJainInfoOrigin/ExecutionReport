import pandas as pd
from sqlalchemy import create_engine, text
import json
import os
from datetime import datetime
import time
import psycopg2

postgresSQLinCloud = False

config = {
  'user': 'postgres',
  'password': 'postgres',
  'host': '127.0.0.1',
  'database': 'postgres',
  'port' : 5432,
  'raise_on_warnings': True
}

configCloud = {
  'user': 'testdbuser',
  'password': 'Scott123',
  'host': 'testdb-pg.postgres.database.azure.com',
  'database': 'portfolio-dev',
  'port' : 5432,
  'raise_on_warnings': True
  
}

tableImpactedRowCount = {
    'feature': 0,
    'featureExecution': 0,
    'scenario' : 0,
    'scenarioStep' :0
}

tableNextValDict = {
    'feature': 0,
    'featureExecution': 0,
    'scenario' : 0,
    'scenarioStep' :0
}

#_______________________________________________________________________________________


def getFileModifiedTimeStamp(filePath):
    return datetime.fromtimestamp(os.path.getmtime(filePath)).strftime("%Y-%m-%d %H:%M:%S")

#_______________________________________________________________________________________


def getConnection(config):
    if postgresSQLinCloud :
        conn = psycopg2.connect(
        database=config['database'], 
        user=config['user'], 
        password=config['password'], 
        host=config['host'], 
        port=config['port'],
        sslmode="require"
        )
    else:
        conn = psycopg2.connect(
        database=config['database'], 
        user=config['user'], 
        password=config['password'], 
        host=config['host'], 
        port=config['port']
        )

    return conn    
#_______________________________________________________________________________________

def executeSQL(sqlInsert):
    # sqlEngine= getConnection(config)
    # dbConnection= sqlEngine.cursor()
    #print("executeSQL",sqlInsert)
    dbConnection.execute(sqlInsert)
    sqlEngine.commit()
    #dbConnection.close()
    #return result
    #return dbConnection
#_______________________________________________________________________________________

def getAttribute(listItem, searchItem):
    if listItem[searchItem] :
        return listItem[searchItem]
#_______________________________________________________________________________________
def getNextVal(tableName, colName, prefixChar):
    sqlNextVal = f""" select cast(substring({colName},length('{prefixChar}')+1) as int)+1 from {tableName} order by CreatedON desc limit 1;
                """
    #print(sqlNextVal)
    #cast(substring(featureId,length('FE')) as float) + 1
    #sqlEngine= getConnection(config)
    #dbConnection= sqlEngine.cursor()
    
    #result = executeSQL(sqlNextVal)
    executeSQL(sqlNextVal)
    #print("dbConnection.rowcount", dbConnection.rowcount)
    #if result.rowcount ==1:
    if dbConnection.rowcount ==1:
        #print('result.fetchone()[0]', result.rowcount)
        #print(dbConnection.fetchone()[0])
        return dbConnection.fetchone()[0]
    else:
        #print('no records')
        return 1
    

#_______________________________________________________________________________________    

def getNextValAllTable():
    
    tableNextValDict['feature'] = getNextVal('feature', 'featureid', 'F')
    tableNextValDict['featureExecution'] = getNextVal('featureExecution', 'featureExecutionId', 'FE')
    tableNextValDict['scenario'] = getNextVal('scenario', 'scenarioExecutionId', 'SE')
    tableNextValDict['scenarioStep'] = getNextVal('scenariostep', 'ScenarioStepExecutionId', 'SSE')
#_______________________________________________________________________________________


def featureTable(executionData):
    #C5~S4~A9~F2~R1~Save Education
    clientId,sponsorId, applicationId,featureId,releaseId,featureName = getAttribute(executionData, "description").split('~')
    uri = getAttribute(executionData, "title").replace("\\","\\\\")
    description =  "description" #getAttribute(executionData, "suites")
    sqlSelectFeature=f"Select * from Feature where ApplicationId='{applicationId}' and FeatureId='{featureId}';"
    #result = executeSQL(sqlSelectFeature)
    executeSQL(sqlSelectFeature)
    if dbConnection.rowcount <= 0:
        if featureId == "??":
            #featureId = 'F' + str(getNextVal('feature', 'featureid', 'F'))
            featureId = 'F' + str(tableNextValDict['feature'])
            
        sqlInsertFeature = f"""Insert into feature 
        (applicationId, featureid, FeatureName, description, uri, CreatedBy)
        values ('{applicationId}','{featureId}' ,'{featureName}','{description}','{uri}','infoOrigin');"""
        #print ("sql-->", sqlInsertFeature)
        
        executeSQL(sqlInsertFeature)

        tableImpactedRowCount['feature'] = tableImpactedRowCount['feature'] + 1
        tableNextValDict['feature'] = tableNextValDict['feature'] + 1
    return featureId
#_______________________________________________________________________________________

def featureExecutionTable(executionData,featureId,fileModifiedTimeStamp):
    #description: C1~S1~A1~F1~R1~MenuVerifiedBy
    releaseId = getAttribute(executionData, "description").split('~')[4]
    df = pd.json_normalize(executionData,record_path='suites')
    
    #df1= pd.json_normalize(executionData,record_path='stats')
    #print(df)
    
    totalScenario = 0
    for eachspec in df['specs'][0]:
        totalScenario = totalScenario +1 
    
    if 'start_timestamp' in df:
     #   print ('true', df['Title'][0])
        startTime = df['startTime'][0].replace('T',' ').replace('Z', ' ')
    else:
        startTime = fileModifiedTimeStamp
    #featureExecutionId = 'FE' + str(getNextVal('featureExecution', 'featureExecutionId', 'FE'))
    featureExecutionId = 'FE' + str(tableNextValDict['featureExecution'])
    tcDuration=1
    #print ("df['specs']", df['specs'])
    #totalScenario = df['specs'].count()
    #print('totalScenario', totalScenario)
    sqlInsertFeatureExecution = f"""Insert into featureexecution 
    (FeatureExecutionId, featureid, TotalDuration, TotalScenario, StartTime, CreatedBy,releaseId)
    values ('{featureExecutionId}','{featureId}' ,{tcDuration},{totalScenario},'{startTime}','infoOrigin', '{releaseId}');"""
    #print('featureExeutionSQL', sqlInsertFeatureExecution)
    
    executeSQL(sqlInsertFeatureExecution)
    tableImpactedRowCount['featureExecution'] = tableImpactedRowCount['featureExecution'] + 1    
    tableNextValDict['featureExecution'] = tableNextValDict['featureExecution'] + 1  
    return featureExecutionId
#_______________________________________________________________________________________

def scenarioTable(executionData,featureExecutionId):
    df = pd.json_normalize(executionData,record_path='suites')
    #print('executionData-->Title', df['specs'][0])
    #print('executionData-->Title', df)
    #for index, fullScenarioName in enumerate(df['title'].tolist()):
    for index, fullScenarioName in enumerate(df['specs'][0]):
        #scenarioExecutionId = 'SE' + str(getNextVal('scenario', 'scenarioExecutionId', 'SE'))
        #print('fullScenarioName-->', fullScenarioName['title'])
        scenarioExecutionId = 'SE' +  str(tableNextValDict['scenario'])
        #scenarioId = df['tags'][index][0]['name'] if len(df['tags'][index])>0 else 'notags'
        tags = []
        # for i in df['tags'][index]:
        #     tags.append(i['name'])
        
        scenarioId = fullScenarioName['title'].split("~")[0] if "~" in fullScenarioName['title'] else 'TC_Auto'
        scenarioName = fullScenarioName['title'].split("~")[1] if "~" in fullScenarioName['title'] else 'Scenario Name_Auto'
        #description= df['description'][index]
        description = ""
        duration=1
        sqlInsertScenario = f"""Insert into scenario 
        (ScenarioExecutionId, FeatureExecutionId, ScenarioId, ScenarioName, Description, Duration, CreatedBy, tags)
        values ('{scenarioExecutionId}','{featureExecutionId}' ,'{scenarioId}','{scenarioName}','{description}',{duration},'infoOrigin', '{",".join(tags)}');"""
        print('sqlInsertScenario-->', sqlInsertScenario)
        executeSQL(sqlInsertScenario)

        dfScenarioSectionDF = df['specs'][0][index]['tests'][0]['results'][0]['steps']
        #print('dfScenarioSectionDF',index, dfScenarioSectionDF)
        
        scenarioStepTable(dfScenarioSectionDF,scenarioExecutionId,scenarioId)
        tableImpactedRowCount['scenario'] = tableImpactedRowCount['scenario'] + 1  
        tableNextValDict['scenario'] = tableNextValDict['scenario'] + 1       
#_______________________________________________________________________________________

def scenarioStepTable(dfScenarioSection,scenarioExecutionId,scenarioId):
    scenarioStatusFlag = True
    for stepDetail in dfScenarioSection:
        #ScenarioStepExecutionId = 'SSE' + str(getNextVal('scenariostep', 'ScenarioStepExecutionId', 'SSE'))
        ScenarioStepExecutionId = 'SSE' + str(tableNextValDict['scenarioStep'])
        #keyword = stepDetail['keyword'].strip()
        keyword = "Given"
        if 'title' in stepDetail:
            name = stepDetail['title'].replace('"', "'")
        else:
            name = keyword
        #print('stepDetailduration-->', stepDetail['duration'])
        if 'duration' in stepDetail:
            
            duration = round(stepDetail['duration']/pow(10, 3),2)
        else:
            duration = 0
        #status = stepDetail['result']['status']
        status = 'passed'
        if "error" in stepDetail :
            errorMessage = stepDetail['error']['message'].replace('"',"'")
            status = 'failed'
        else:
            errorMessage = " "
        if status.upper() != 'passed'.upper() and scenarioStatusFlag:
            scenarioStatusFlag = False
        sqlInsertScenarioStep = f"""Insert into scenariostep 
                (ScenarioStepExecutionId,ScenarioExecutionId, ScenarioId, Keyword, Name, Duration, Status, ErrorMessage,CreatedBy)
            values ('{ScenarioStepExecutionId}','{scenarioExecutionId}' ,'{scenarioId}','{keyword}','{name.replace("'", "''")}',{duration}, '{status}', '{errorMessage.replace("'", "''")}' ,'infoOrigin')"""
        #print('sqlInsertScenarioStep--', sqlInsertScenarioStep)
        executeSQL(sqlInsertScenarioStep)
        tableImpactedRowCount['scenarioStep'] = tableImpactedRowCount['scenarioStep'] + 1   
        tableNextValDict['scenarioStep'] = tableNextValDict['scenarioStep'] + 1 
        time.sleep(1/3000)
    
    scenarioStatus ='passed' if scenarioStatusFlag else 'failed'
    sqlUpdateScenario = f"""update scenario set status='{scenarioStatus}'
    where scenarioId='{scenarioId}' and ScenarioExecutionId='{scenarioExecutionId}';"""
    executeSQL(sqlUpdateScenario)
#_______________________________________________________________________________________

def databaseCummulative(executionStartTime):
#Update duration
    sqlUpdateScenario = f"""UPDATE scenario s SET duration = x.total
                        FROM (SELECT ScenarioExecutionId, SUM(duration) as total
                        FROM scenarioStep
                        where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}'
                        GROUP BY ScenarioExecutionId
                        ) x 
                        WHERE s.ScenarioExecutionId = x.ScenarioExecutionId;"""

    executeSQL(sqlUpdateScenario)
#Update Total Steps
    sqlUpdateScenario = f"""UPDATE scenario s SET steps = x.total
                        FROM (SELECT ScenarioExecutionId, count(duration) as total
                        FROM scenarioStep
                        where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}'
                        GROUP BY ScenarioExecutionId
                        ) x 
                        WHERE s.ScenarioExecutionId = x.ScenarioExecutionId;"""

    executeSQL(sqlUpdateScenario)

#Update Failed number
    sqlUpdateFeatureExecution=f"""UPDATE featureexecution FE SET failed = x.total, FailedDuration=x.failedDuration
                FROM (
                SELECT FeatureExecutionId, count(*) as total,sum(duration) as failedDuration
                FROM scenario
                where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}' and status='failed'
                GROUP BY FeatureExecutionId
                ) x 
                WHERE FE.FeatureExecutionId = x.FeatureExecutionId;"""
    executeSQL(sqlUpdateFeatureExecution)
#Update Passed number
    sqlUpdateFeatureExecution=f"""UPDATE featureexecution FE SET passed = x.total, PassedDuration=x.passedDuration
                FROM (
                SELECT FeatureExecutionId, count(*) as total,sum(duration) as passedDuration
                FROM scenario
                where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}' and status='passed'
                GROUP BY FeatureExecutionId
                ) x 
                WHERE FE.FeatureExecutionId = x.FeatureExecutionId ;"""
    executeSQL(sqlUpdateFeatureExecution)

#Update duration
    sqlUpdateFeatureExecution=f"""UPDATE featureexecution FE SET Totalduration = x.total
                FROM (
                SELECT FeatureExecutionId, sum(duration) as total
                FROM scenario
                where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}'
                GROUP BY FeatureExecutionId
                ) x 
                WHERE FE.FeatureExecutionId = x.FeatureExecutionId ;"""
    executeSQL(sqlUpdateFeatureExecution)
#_______________________________________________________________________________________
def processJSON(cucumberTestRunFile, executionStartTime,fileModifiedTimeStamp):
    executionData = json.load(open(cucumberTestRunFile))
    #print('executionData', executionData)
    for indexExecutionData, featureFile in enumerate(executionData["suites"]):
        #print('featureFile->',featureFile)
        featureId = featureTable(featureFile)
        featureExecutionId = featureExecutionTable(featureFile,featureId,fileModifiedTimeStamp)
        scenarioTable(featureFile,featureExecutionId)
        databaseCummulative(executionStartTime)
#_______________________________________________________________________________________
def printRowsAdded():
    for k, v in tableImpactedRowCount.items():
        print(f"""{v} row(s) added to {k} Table""")
    for key in tableImpactedRowCount.keys():
        tableImpactedRowCount[key] = 0
#_______________________________________________________________________________________

if postgresSQLinCloud :
    for key in config.keys():
        config[key] = configCloud[key]
sqlEngine= getConnection(config)
dbConnection= sqlEngine.cursor()
getNextValAllTable()