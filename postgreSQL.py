import pandas as pd
from sqlalchemy import create_engine, text
import json
import os, getopt, sys
from datetime import datetime
import shutil
from masterFunction import *

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
    executionStartTime = datetime.now()
    sqlSelectTimeStamp=f"Select current_timestamp;"
    #result = executeSQL(sqlSelectTimeStamp)
    executeSQL(sqlSelectTimeStamp)
    executionSQLStartTime =dbConnection.fetchone()[0]
    inboundPath, processedPath = main(sys.argv[1:])
    dir_list = os.listdir(inboundPath)
    for cucumberTestRunFile in dir_list:
        fileModifiedTimeStamp=getFileModifiedTimeStamp(inboundPath + '/' + cucumberTestRunFile)
        os.chdir(inboundPath)
        executionData = json.load(open(cucumberTestRunFile))
        preValidation= "Passed"
        preValidationMsg = cucumberTestRunFile + " is not processed as\n"
        for indexExecutionData, featureFile in enumerate(executionData):
            df = pd.json_normalize(featureFile,record_path='elements')
            if featureFile['description'].count('~') <4 :
                preValidation="Failed"
                preValidationMsg = f"""{preValidationMsg} Feature Description is missing in \n #{featureFile['uri']} \n"""
            # for index, data in enumerate(df['tags']):
            #     if len(data) ==0 :
            #         preValidation = "Failed"
            #         preValidationMsg = f"""{preValidationMsg} Scenario/Testcase first Tag having unique TCid is missing in\n -{executionData[indexExecutionData]['elements'][index]['name']}"""

        if preValidation =="Failed" :
            print(preValidationMsg)
        else:
            processJSON(cucumberTestRunFile,executionSQLStartTime,fileModifiedTimeStamp)
            print("Successfully processed file...", cucumberTestRunFile)
            printRowsAdded()
            shutil.move( inboundPath + "/" + cucumberTestRunFile, processedPath +'/' + cucumberTestRunFile,)

    executionEndTime = datetime.now()
    print('Total Execution Time=', executionEndTime - executionStartTime)



