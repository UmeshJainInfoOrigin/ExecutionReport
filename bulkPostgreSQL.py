import pandas as pd
from sqlalchemy import create_engine, text
import json
import os, getopt, sys
from datetime import datetime
import shutil
import psycopg2
import csv
#_______________________________________________________________________________________

postgresSQLinCloud = False
dataFilePath = os.getcwd() + "/dataFile/"
#print("dataFilePath", dataFilePath)
config = {
  'user': 'postgres',
  'password': 'postgres',
  'host': '127.0.0.1',
  'database': 'postgres',
  'port' : 5432,
  'raise_on_warnings': True,
  #'sslmode': "require",
  'ssl_ca': 'PostgresDigiCertGlobalRootCA.crt.pem',
  'schema': 'public'
}

configCloud = {
  'user': 'testdbuser',
  'password': 'Scott123',
  'host': 'testdb-pg.postgres.database.azure.com',
  'database': 'test',
  'port' : 5432,
  'raise_on_warnings': True,
  #'sslmode': "require",
  'ssl_ca': os.getcwd() + '/PostgresDigiCertGlobalRootCA.crt.pem',
  'schema': 'public'
}

tableNextValDict = {
    'feature': 0,
    'featureExecution': 0,
    'scenario' : 0,
    'scenarioStep' :0
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
        #sslmode=config['sslmode']
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
    sqlNextVal = f""" select cast(substring({colName},length('{prefixChar}')+1) as int)+1 
    from {tableName} order by cast(substring({colName},length('{prefixChar}')+1) as int) desc limit 1;
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

def getNextValAllTable():
    
    tableNextValDict['feature'] = getNextVal('feature', 'featureid', 'F')
    tableNextValDict['featureExecution'] = getNextVal('featureExecution', 'featureExecutionId', 'FE')
    tableNextValDict['scenario'] = getNextVal('scenario', 'scenarioExecutionId', 'SE')
    tableNextValDict['scenarioStep'] = getNextVal('scenariostep', 'ScenarioStepExecutionId', 'SSE')
    #print('tableNextValDict=', tableNextValDict)
#_______________________________________________________________________________________    
def createFileWithHeader(fileName, header):
    with open(dataFilePath + fileName + '.csv', 'w', newline='') as f:
        writer=csv.writer(f, delimiter=';',  quoting=csv.QUOTE_ALL)
        #header = ["applicationid","featureid","featurename","description","uri","createdby","createdon"]
        
        writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_ALL)
        writer.writeheader()
#_______________________________________________________________________________________    
def writeToFile(fileName, columnData):
    with open(dataFilePath + fileName + '.csv', 'a', newline='') as f:
        writer=csv.writer(f, delimiter=';',  quoting=csv.QUOTE_ALL)
        writer.writerow(columnData)
#_______________________________________________________________________________________    
def loadDataUsingCopy(tableName, tableFields, tablePrimaryKey):
    copyFeature = f"""create temporary table import_{tableName} as select {tableFields} from {tableName} limit 0;
        copy import_{tableName}({tableFields}) from '{dataFilePath}{tableName}.csv' DELIMITER ';' 
                    CSV header QUOTE AS  '"' ;

        begin transaction;
            delete  from {tableName}
            where   {tablePrimaryKey} in
                    (
                    select  {tablePrimaryKey}
                    from    import_{tableName}
                    );
            insert  into {tableName}({tableFields})
            select  {tableFields}
            from    import_{tableName};
        commit transaction; """
    #print("copyFeature=", copyFeature)
    executeSQL(copyFeature)
#_______________________________________________________________________________________    
def removeFiles():
    for f in os.listdir(dataFilePath):
        os.remove(os.path.join(dataFilePath, f))
#_______________________________________________________________________________________    
def featureTable(executionData):
    columnData = []
    clientId,sponsorId, applicationId,featureId,featureName = getAttribute(executionData, "description").split('~')
    uri = getAttribute(executionData, "uri").replace("\\","\\\\")
    description = getAttribute(executionData, "name")
    sqlSelectFeature=f"Select * from Feature where ApplicationId='{applicationId}' and FeatureId='{featureId}';"
    result = executeSQL(sqlSelectFeature)
    if result.rowcount <= 0:
        if featureId == "??":
            #featureId = 'F' + str(getNextVal('feature', 'featureid', 'F'))
            featureId = 'F' + str(tableNextValDict['feature'])
        sqlInsertFeature = f"""Insert into feature 
        (applicationId, featureid, FeatureName, description, uri, CreatedBy)
        values ('{applicationId}','{featureId}' ,'{featureName}','{description}','{uri}','infoOrigin');"""
        columnData.append(applicationId)
        columnData.append(featureId)
        columnData.append(featureName)
        columnData.append(description)
        columnData.append(uri)
        columnData.append('Info Origin')
        writeToFile('feature', columnData)
        #executeSQL(sqlInsertFeature)
        tableImpactedRowCount['feature'] = tableImpactedRowCount['feature'] + 1
        tableNextValDict['feature'] = tableNextValDict['feature'] + 1
    return featureId
#_______________________________________________________________________________________

def featureExecutionTable(executionData,featureId):
    columnData = []
    df = pd.json_normalize(executionData,record_path='elements')
    if 'start_timestamp' in df:
        startTime = df['start_timestamp'][0].replace('T',' ').replace('Z', ' ')
    else:
        startTime = getFileModifiedTimeStamp(os.getcwd() + '/' + cucumberTestRunFile)

    #featureExecutionId = 'FE' + str(getNextVal('featureExecution', 'featureExecutionId', 'FE'))
    featureExecutionId = 'FE' + str(tableNextValDict['featureExecution'])
    tcDuration=1
    totalScenario = df['steps'].count()
    sqlInsertFeatureExecution = f"""Insert into featureexecution 
    (FeatureExecutionId, featureid, TotalDuration, TotalScenario, StartTime, CreatedBy)
    values ('{featureExecutionId}','{featureId}' ,{tcDuration},{totalScenario},'{startTime}','infoOrigin');"""
    columnData.append(featureExecutionId)
    columnData.append(featureId)
    columnData.append(tcDuration)
    columnData.append(totalScenario)
    columnData.append(startTime)
    columnData.append('Info Origin')
    writeToFile('featureexecution', columnData)
    #executeSQL(sqlInsertFeatureExecution)
    tableImpactedRowCount['featureExecution'] = tableImpactedRowCount['featureExecution'] + 1
    tableNextValDict['featureExecution'] = tableNextValDict['featureExecution'] + 1  
    return featureExecutionId
#_______________________________________________________________________________________

def scenarioTable(executionData,featureExecutionId):
    
    df = pd.json_normalize(executionData,record_path='elements')
    for index, scenarioName in enumerate(df['name'].tolist()):
        columnData = []
        #scenarioExecutionId = 'SE' + str(getNextVal('scenario', 'scenarioExecutionId', 'SE'))
        scenarioExecutionId = 'SE' + str(tableNextValDict['scenario'])
        scenarioId = df['tags'][index][0]['name'] if len(df['tags'][index])>0 else 'notags'
        description= df['description'][index]
        duration=1
        sqlInsertScenario = f"""Insert into scenario 
        (ScenarioExecutionId, FeatureExecutionId, ScenarioId, ScenarioName, Description, Duration, CreatedBy)
        values ('{scenarioExecutionId}','{featureExecutionId}' ,'{scenarioId}','{scenarioName}','{description}',{duration},'infoOrigin');"""
        #executeSQL(sqlInsertScenario)
        columnData.append(scenarioExecutionId)
        columnData.append(featureExecutionId)
        columnData.append(scenarioId)
        columnData.append(scenarioName)
        columnData.append(description)
        columnData.append(duration)
        columnData.append('Info Origin')
        writeToFile('scenario', columnData)
        dfScenarioSectionDF = df['steps'][index]
        scenarioStepTable(dfScenarioSectionDF,scenarioExecutionId,scenarioId)
        tableImpactedRowCount['scenario'] = tableImpactedRowCount['scenario'] + 1
        tableNextValDict['scenario'] = tableNextValDict['scenario'] + 1      
#_______________________________________________________________________________________

def scenarioStepTable(dfScenarioSection,scenarioExecutionId,scenarioId):
    scenarioStatusFlag = True
    for stepDetail in dfScenarioSection:
        columnData = []
        #ScenarioStepExecutionId = 'SSE' + str(getNextVal('scenariostep', 'ScenarioStepExecutionId', 'SSE'))
        ScenarioStepExecutionId = 'SSE' + str(tableNextValDict['scenarioStep'])
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
        #executeSQL(sqlInsertScenarioStep)
        columnData.append(ScenarioStepExecutionId)
        columnData.append(scenarioExecutionId)
        columnData.append(scenarioId)
        columnData.append(keyword)
        columnData.append(name.replace("'", "''"))
        columnData.append(duration)
        columnData.append(status)
        columnData.append(errorMessage.replace("'", "''"))
        columnData.append('Info Origin')
        writeToFile('scenariostep', columnData)

        tableImpactedRowCount['scenarioStep'] = tableImpactedRowCount['scenarioStep'] + 1 
        tableNextValDict['scenarioStep'] = tableNextValDict['scenarioStep'] + 1         
    
    scenarioStatus ='passed' if scenarioStatusFlag else 'failed'
    sqlUpdateScenario = f"""update scenario set status='{scenarioStatus}'
    where scenarioId='{scenarioId}' and ScenarioExecutionId='{scenarioExecutionId}';"""
    #executeSQL(sqlUpdateScenario)
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
#update status in scenario from scenarioStep
    sqlUpdateScenario = f"""UPDATE scenario s SET status = x.status
                        FROM (select distinct ScenarioExecutionId,
                        case when exists (select 1 from scenariostep t2 where t1.ScenarioExecutionId = T2.ScenarioExecutionId and (T2.status = 'failed' or T2.status='skipped')) then 'failed' else 'passed' end as status
                        from scenariostep t1
                        where createdon >= '{executionStartTime.strftime("%Y-%m-%d %H:%M:%S")}'
                        ) x 
                        WHERE s.ScenarioExecutionId = x.ScenarioExecutionId"""
    #print(sqlUpdateScenario)
    executeSQL(sqlUpdateScenario)
#_______________________________________________________________________________________
def processJSON(cucumberTestRunFile, executionStartTime):
    
    executionData = json.load(open(cucumberTestRunFile))
    for indexExecutionData, featureFile in enumerate(executionData):
        featureId = featureTable(featureFile)
        featureExecutionId = featureExecutionTable(featureFile,featureId)
        scenarioTable(featureFile,featureExecutionId)
        
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

    getNextValAllTable()
    createFileWithHeader(fileName='feature', header = ["applicationid","featureid","featurename","description","uri","createdby"])
    createFileWithHeader(fileName='featureExecution', header = ["featureexecutionId", "featureid", "totalduration", "TotalScenario", "StartTime", "CreatedBy"])
    createFileWithHeader(fileName='scenario', header = ["ScenarioExecutionId", "FeatureExecutionId", "ScenarioId", "ScenarioName", "Description", "Duration", "CreatedBy"])
    createFileWithHeader(fileName='scenariostep', header = ["FeatureExecutionId", "featureid", "TotalDuration", "TotalScenario", "StartTime", "CreatedBy"])
    
    #writeToFile()
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
            print("_________________________________________________")
            shutil.move( inboundPath + "/" + cucumberTestRunFile, processedPath +'/' + cucumberTestRunFile,)
            #Feature
            loadDataUsingCopy('feature','applicationid,featureid,featurename,description,uri,createdby','featureid')
            #FeatureExecution
            loadDataUsingCopy('featureexecution','featureexecutionId, featureid, totalduration, TotalScenario, StartTime, CreatedBy','featureexecutionId')
            #Scenario
            loadDataUsingCopy('scenario','ScenarioExecutionId, FeatureExecutionId, ScenarioId, ScenarioName, Description, Duration, CreatedBy', 'ScenarioExecutionId')
            #ScenarioStep
            loadDataUsingCopy('scenariostep','ScenarioStepExecutionId,ScenarioExecutionId, ScenarioId, Keyword, Name, Duration, Status, ErrorMessage,CreatedBy', 'ScenarioStepExecutionId')
            databaseCummulative(executionStartTime)
            removeFiles()
    #executeSQL(copyFeatureExecution)
    #FeatureExecutionId, featureid, TotalDuration, TotalScenario, StartTime, CreatedBy
    
    executionEndTime = datetime.now()
    print('Total Execution Time=', executionEndTime - executionStartTime)



