import pandas as pd
from sqlalchemy import create_engine, text
import json
import os, getopt, sys
from datetime import datetime
import shutil
import psycopg2
#_______________________________________________________________________________________

postgresSQLinCloud = True

config = {
  'user': 'postgres',
  'password': 'postgres',
  'host': '127.0.0.1',
  'database': 'postgres',
  'port' : 5432,
  'raise_on_warnings': True,
  'sslmode': "require",
  'ssl_ca': 'PostgresDigiCertGlobalRootCA.crt.pem'
}

configCloud = {
  'user': 'testdbuser',
  'password': 'Scott123',
  'host': 'testdb-pg.postgres.database.azure.com',
  'database': 'test',
  'port' : 5432,
  'raise_on_warnings': True,
  'sslmode': "require",
  'ssl_ca': os.getcwd() + '/PostgresDigiCertGlobalRootCA.crt.pem'
}

tableImpactedRowCount = {
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
        sslmode=config['sslmode']
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
    sqlEngine= getConnection(config)
    dbConnection= sqlEngine.cursor()
    dbConnection.execute(sqlInsert)
    sqlEngine.commit()
    #dbConnection.close()
    #return result
    return dbConnection
#_______________________________________________________________________________________

def getAttribute(listItem, searchItem):
    #print('listItem', listItem[searchItem])
    # for item in listItem:
    #     print('return from here')
    #     return item[searchItem]
    #return "null~"    
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
    
    result = executeSQL(sqlNextVal)
    if result.rowcount ==1:
        #print('result.fetchone()[0]', result.rowcount)
        #print(result.fetchone()[0])
        return result.fetchone()[0]
    else:
        #print('no records')
        return 1
    

    #result = dbConnection.execute(sqlNextVal)

    #dbConnection.close()
    #return int(result[0])
#_______________________________________________________________________________________    

def featureTable(executionData):
    clientId,sponsorId, applicationId,featureId,featureName = getAttribute(executionData, "description").split('~')
    uri = getAttribute(executionData, "uri").replace("\\","\\\\")
    description = getAttribute(executionData, "name")
    sqlSelectFeature=f"Select * from Feature where ApplicationId='{applicationId}' and FeatureId='{featureId}';"
    result = executeSQL(sqlSelectFeature)
    if result.rowcount <= 0:
        if featureId == "??":
            featureId = 'F' + str(getNextVal('feature', 'featureid', 'F'))
        sqlInsertFeature = f"""Insert into feature 
        (applicationId, featureid, FeatureName, description, uri, CreatedBy)
        values ('{applicationId}','{featureId}' ,'{featureName}','{description}','{uri}','infoOrigin');"""
        executeSQL(sqlInsertFeature)
        tableImpactedRowCount['feature'] = tableImpactedRowCount['feature'] + 1
    return featureId
#_______________________________________________________________________________________

def featureExecutionTable(executionData,featureId):
    df = pd.json_normalize(executionData,record_path='elements')
    if 'start_timestamp' in df:
        startTime = df['start_timestamp'][0].replace('T',' ').replace('Z', ' ')
    else:
        startTime = getFileModifiedTimeStamp(os.getcwd() + '/' + cucumberTestRunFile)

    featureExecutionId = 'FE' + str(getNextVal('featureExecution', 'featureExecutionId', 'FE'))
    tcDuration=1
    totalScenario = df['steps'].count()
    sqlInsertFeatureExecution = f"""Insert into featureexecution 
    (FeatureExecutionId, featureid, TotalDuration, TotalScenario, StartTime, CreatedBy)
    values ('{featureExecutionId}','{featureId}' ,{tcDuration},{totalScenario},'{startTime}','infoOrigin');"""
    executeSQL(sqlInsertFeatureExecution)
    tableImpactedRowCount['featureExecution'] = tableImpactedRowCount['featureExecution'] + 1    
    return featureExecutionId
#_______________________________________________________________________________________

def scenarioTable(executionData,featureExecutionId):
    df = pd.json_normalize(executionData,record_path='elements')
    for index, scenarioName in enumerate(df['name'].tolist()):
        scenarioExecutionId = 'SE' + str(getNextVal('scenario', 'scenarioExecutionId', 'SE'))
        scenarioId = df['tags'][index][0]['name'] if len(df['tags'][index])>0 else 'notags'
        description= df['description'][index]
        duration=1
        sqlInsertScenario = f"""Insert into scenario 
        (ScenarioExecutionId, FeatureExecutionId, ScenarioId, ScenarioName, Description, Duration, CreatedBy)
        values ('{scenarioExecutionId}','{featureExecutionId}' ,'{scenarioId}','{scenarioName}','{description}',{duration},'infoOrigin');"""
        executeSQL(sqlInsertScenario)
        dfScenarioSectionDF = df['steps'][index]
        scenarioStepTable(dfScenarioSectionDF,scenarioExecutionId,scenarioId)
        tableImpactedRowCount['scenario'] = tableImpactedRowCount['scenario'] + 1    
#_______________________________________________________________________________________

def scenarioStepTable(dfScenarioSection,scenarioExecutionId,scenarioId):
    scenarioStatusFlag = True
    for stepDetail in dfScenarioSection:
        ScenarioStepExecutionId = 'SSE' + str(getNextVal('scenariostep', 'ScenarioStepExecutionId', 'SSE'))
        keyword = stepDetail['keyword'].strip()
        name = stepDetail['name'].replace('"', "'")
        if 'duration' in stepDetail['result']:
            duration = round(stepDetail['result']['duration']/pow(10, 9),2)
        else:
            duration = 0
        status = stepDetail['result']['status']
        if "error_message" in stepDetail['result'] :
            errorMessage = stepDetail['result']['error_message'].replace('"',"'")
        else:
            errorMessage = " "
        if status.upper() != 'passed'.upper() and scenarioStatusFlag:
            scenarioStatusFlag = False
        sqlInsertScenarioStep = f"""Insert into scenariostep 
                (ScenarioStepExecutionId,ScenarioExecutionId, ScenarioId, Keyword, Name, Duration, Status, ErrorMessage,CreatedBy)
            values ('{ScenarioStepExecutionId}','{scenarioExecutionId}' ,'{scenarioId}','{keyword}','{name.replace("'", "''")}',{duration}, '{status}', '{errorMessage.replace("'", "''")}' ,'infoOrigin')"""
        #print(sqlInsertScenarioStep)
        executeSQL(sqlInsertScenarioStep)
        tableImpactedRowCount['scenarioStep'] = tableImpactedRowCount['scenarioStep'] + 1    
    
    scenarioStatus ='passed' if scenarioStatusFlag else 'failed'
    sqlUpdateScenario = f"""update scenario set status='{scenarioStatus}'
    where scenarioId='{scenarioId}' and ScenarioExecutionId='{scenarioExecutionId}';"""
    executeSQL(sqlUpdateScenario)
#_______________________________________________________________________________________

def databaseCummulative(executionStartTime):
    sqlUpdateScenario = f"""UPDATE scenario s SET duration = x.total
                        FROM (SELECT ScenarioExecutionId, SUM(duration) as total
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
def processJSON(cucumberTestRunFile, executionStartTime):
    executionData = json.load(open(cucumberTestRunFile))
    for indexExecutionData, featureFile in enumerate(executionData):
        featureId = featureTable(featureFile)
        featureExecutionId = featureExecutionTable(featureFile,featureId)
        scenarioTable(featureFile,featureExecutionId)
        databaseCummulative(executionStartTime)
#_______________________________________________________________________________________
def printRowsAdded():
    for k, v in tableImpactedRowCount.items():
        print(f"""{v} row(s) added to {k} Table""")
    for key in tableImpactedRowCount.keys():
        tableImpactedRowCount[key] = 0
#_______________________________________________________________________________________
def main(argv):
    inboundPath = os.getcwd() + "\\inboundJSONReports"
    processedPath = os.getcwd() + "\\processedJSONReports"
    
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","pfile="])
    except getopt.GetoptError:
        print ('<programname> -i <inboundJSONReportsPath> -p <processedJSONReportsPath>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('<filename> -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile", "--i"):
            inboundPath = arg
        elif opt in ("-p", "--pfile", "--p"):
            processedPath = arg
            # check if directory exists or not yet
            if not os.path.exists(arg):
                os.makedirs(arg)
                print(arg, ' Directory Created....')

    return inboundPath, processedPath
#_______________________________________________________________________________________
if __name__ == '__main__':
    if postgresSQLinCloud :
        for key in config.keys():
            config[key] = configCloud[key]

    executionStartTime = datetime.now()
    sqlSelectTimeStamp=f"Select current_timestamp;"
    result = executeSQL(sqlSelectTimeStamp)
    executionSQLStartTime =result.fetchone()[0]
    inboundPath, processedPath = main(sys.argv[1:])
    dir_list = os.listdir(inboundPath)
    for cucumberTestRunFile in dir_list:
        os.chdir(inboundPath)
        executionData = json.load(open(cucumberTestRunFile))
        preValidation= "Passed"
        preValidationMsg = cucumberTestRunFile + " is not processed as\n"
        for indexExecutionData, featureFile in enumerate(executionData):
            df = pd.json_normalize(featureFile,record_path='elements')
            if featureFile['description'].count('~') <4 :
                preValidation="Failed"
                preValidationMsg = f"""{preValidationMsg} Feature Description is missing in \n #{featureFile['uri']} \n"""
            for index, data in enumerate(df['tags']):
                if len(data) ==0 :
                    preValidation = "Failed"
                    preValidationMsg = f"""{preValidationMsg} Scenario/Testcase first Tag having unique TCid is missing in\n -{executionData[indexExecutionData]['elements'][index]['name']}"""

        if preValidation =="Failed" :
            print(preValidationMsg)
        else:
            processJSON(cucumberTestRunFile,executionSQLStartTime)
            print("Successfully processed file...", cucumberTestRunFile)
            printRowsAdded()
            shutil.move( inboundPath + "/" + cucumberTestRunFile, processedPath +'/' + cucumberTestRunFile,)

    executionEndTime = datetime.now()
    print('Total Execution Time=', executionEndTime - executionStartTime)



