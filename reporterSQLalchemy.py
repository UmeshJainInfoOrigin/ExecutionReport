import pandas as pd
from sqlalchemy import create_engine, text
import pymysql
import json
import os, getopt, sys
from datetime import datetime
import shutil

config = {
  'user': 'root',
  'password': 'MyNewPass',
  'host': '127.0.0.1',
  'database': 'test',
  'port' : 3306,
  'raise_on_warnings': True
}
tableImpactedRowCount = {
    'feature': 0,
    'featureExecution': 0,
    'scenario' : 0,
    'scenarioStep' :0
}

def getFileModifiedTimeStamp(filePath):
    return datetime.fromtimestamp(os.path.getmtime(filePath)).strftime("%Y-%m-%d %H:%M:%S")

def get_connection(config):
    return create_engine(
        url="mysql+pymysql://{0}:{1}@{2}:{3}/{4}".format(
            config['user'], config['password'], config['host'], config['port'], config['database']
        ),echo = False
    )

def executeSqlInsert(sqlInsert):
    sqlEngine= get_connection(config)
    dbConnection= sqlEngine.connect()
    result=dbConnection.execute(text(sqlInsert))
    dbConnection.commit()
    dbConnection.close()
    return result

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
    return int(result[0])
    
def featureTable(executionData):
    clientId,sponsorId, applicationId,featureId,featureName = getAttribute(executionData, "description").split('~')
    uri = getAttribute(executionData, "uri").replace("\\","\\\\")
    description = getAttribute(executionData, "name")
    sqlSelectFeature=f"Select * from Feature where ApplicationId='{applicationId}' and FeatureId='{featureId}';"
    result = executeSqlInsert(sqlSelectFeature)
    if result.rowcount <= 0:
        if featureId == "??":
            featureId = 'F' + str(getNextVal('feature', 'featureid', 'F'))
        sqlInsertFeature = f"""Insert into {config['database']}.feature 
        (applicationId, featureid, FeatureName, description, uri, CreatedBy)
        values ('{applicationId}','{featureId}' ,'{featureName}','{description}','{uri}','infoOrigin');"""
        executeSqlInsert(sqlInsertFeature)
        tableImpactedRowCount['feature'] = tableImpactedRowCount['feature'] + 1
    return featureId

def featureExecutionTable(executionData,featureId):
    df = pd.json_normalize(executionData,record_path='elements')
    if 'start_timestamp' in df:
        startTime = df['start_timestamp'][0].replace('T',' ').replace('Z', ' ')
    else:
        startTime = getFileModifiedTimeStamp(os.getcwd() + '/' + cucumberTestRunFile)

    featureExecutionId = 'FE' + str(getNextVal('featureExecution', 'featureExecutionId', 'FE'))
    tcDuration=1
    totalScenario = df['steps'].count()
    sqlInsertFeatureExecution = f"""Insert into {config['database']}.featureexecution 
    (FeatureExecutionId, featureid, Duration, TotalScenario, StartTime, CreatedBy)
    values ('{featureExecutionId}','{featureId}' ,{tcDuration},{totalScenario},'{startTime}','infoOrigin');"""
    executeSqlInsert(sqlInsertFeatureExecution)
    tableImpactedRowCount['featureExecution'] = tableImpactedRowCount['featureExecution'] + 1    
    return featureExecutionId

def scenarioTable(executionData,featureExecutionId):
    df = pd.json_normalize(executionData,record_path='elements')
    for index, scenarioName in enumerate(df['name'].tolist()):
        scenarioExecutionId = 'SE' + str(getNextVal('scenario', 'scenarioExecutionId', 'SE'))
        scenarioId = df['tags'][index][0]['name'] if len(df['tags'][index])>0 else 'notags'
        description= df['description'][index]
        duration=1
        sqlInsertScenario = f"""Insert into {config['database']}.scenario 
        (ScenarioExecutionId, FeatureExecutionId, ScenarioId, ScenarioName, Description, Duration, CreatedBy)
        values ('{scenarioExecutionId}','{featureExecutionId}' ,'{scenarioId}','{scenarioName}','{description}',{duration},'infoOrigin');"""
        executeSqlInsert(sqlInsertScenario)
        dfScenarioSectionDF = df['steps'][index]
        scenarioStepTable(dfScenarioSectionDF,scenarioExecutionId,scenarioId)
        tableImpactedRowCount['scenario'] = tableImpactedRowCount['scenario'] + 1    

def scenarioStepTable(dfScenarioSection,scenarioExecutionId,scenarioId):
    scenarioStatusFlag = True
    for stepDetail in dfScenarioSection:
        ScenarioStepExecutionId = 'SSE' + str(getNextVal('scenariostep', 'ScenarioStepExecutionId', 'SSE'))
        keyword = stepDetail['keyword'].strip()
        name = stepDetail['name'].replace('"', "'")
        duration = round(stepDetail['result']['duration']/pow(10, 9),2)
        status = stepDetail['result']['status']
        if "error_message" in stepDetail['result'] :
            errorMessage = stepDetail['result']['error_message'].replace('"',"'")
        else:
            errorMessage = ""
        if status.upper() != 'passed'.upper() and scenarioStatusFlag:
            scenarioStatusFlag = False
        sqlInsertScenarioStep = f"""Insert into {config['database']}.scenariostep 
                (ScenarioStepExecutionId,ScenarioExecutionId, ScenarioId, Keyword, Name, Duration, Status, ErrorMessage,CreatedBy)
            values ('{ScenarioStepExecutionId}','{scenarioExecutionId}' ,'{scenarioId}','{keyword}',"{name}",{duration}, '{status}', "{errorMessage}" ,'infoOrigin')"""
        executeSqlInsert(sqlInsertScenarioStep)
        tableImpactedRowCount['scenarioStep'] = tableImpactedRowCount['scenarioStep'] + 1    
    
    scenarioStatus ='passed' if scenarioStatusFlag else 'failed'
    sqlUpdateScenario = f"""update {config['database']}.scenario set status='{scenarioStatus}'
    where scenarioId='{scenarioId}' and ScenarioExecutionId='{scenarioExecutionId}';"""
    executeSqlInsert(sqlUpdateScenario)

def databaseCummulative(executionStartTime):
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

#Update duration
    sqlUpdateFeatureExecution=f"""UPDATE {config['database']}.featureexecution FE
                INNER JOIN (
                SELECT FeatureExecutionId, sum(duration) as total
                FROM test.scenario
                where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}'
                GROUP BY FeatureExecutionId
                ) x ON FE.FeatureExecutionId = x.FeatureExecutionId 
                SET FE.duration = x.total;"""
    executeSqlInsert(sqlUpdateFeatureExecution)

def processJSON(cucumberTestRunFile, executionStartTime):
    executionData = json.load(open(cucumberTestRunFile))
    for indexExecutionData, featureFile in enumerate(executionData):
        featureId = featureTable(featureFile)
        featureExecutionId = featureExecutionTable(featureFile,featureId)
        scenarioTable(featureFile,featureExecutionId)
        databaseCummulative(executionStartTime)

def printRowsAdded():
    for k, v in tableImpactedRowCount.items():
        print(f"""{v} row(s) added to {k} Table""")
    for key in tableImpactedRowCount.keys():
        tableImpactedRowCount[key] = 0

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

if __name__ == '__main__':
    executionStartTime = datetime.now()
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
            processJSON(cucumberTestRunFile,executionStartTime)
            print("Successfully processed file...", cucumberTestRunFile)
            printRowsAdded()
            shutil.move( inboundPath + "/" + cucumberTestRunFile, processedPath +'/' + cucumberTestRunFile,)

    executionEndTime = datetime.now()
    print('Total Execution Time=', executionEndTime - executionStartTime)



