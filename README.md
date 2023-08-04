# ExecutionReport

Installation
pip install mysql-connector-python
pip install pandas
pip install sqlalchemy
pip install pymysql

pip freeze > package.txt        |  This will get all the dependency into package.txt
pip install -r package.txt      | This will install dependency

https://medium.com/swlh/converting-nested-json-structures-to-pandas-dataframes-e8106c59976e
i am learning GIT

## ?? should be placed in feature description first time ONLY
## every TC should have first tag as its testcase unique id for that particular file example @TC01
## feature file should use single quote(') for passing any data from GIVEN/WHEN/THEN keywords

## My SQL Server 
To resolve the issue
Error Code: 1175. You are using safe update mode and you tried to update a table without a WHERE that uses a KEY column. 

use this command SET SQL_SAFE_UPDATES = 0;

# Configuration
* Insert Data into 3 Master Tables
- Client Table

    ClientID | ClientName | Description | CreatedBy | CreatedOn
    --- | --- | --- | --- |--- 
    C1 | Dell | BFSI | 24-Jul-23  | InfoOrigin 
    C2 | HP | Laptop | 22-Jul-23  | InfoOrigin 

- ClientSponsor Table
    ClientID | SponsorID | Sponsor Name | Designation | Department | CreatedBy | CreatedOn
    --- | --- | --- | --- |--- |--- |--- 
    C1 | S1 | John | VP | Testing |24-Jul-23  | InfoOrigin 
    C2 | S2 | Adam | AVP | QA | 22-Jul-23  | InfoOrigin 

- Application Table
    SponsorID | ApplicationID |Application Name | Description | CreatedBy | CreatedOn
    --- | --- | --- | --- |--- |--- 
    S1 | A1 | PDF | Generates report | 24-Jul-23  | InfoOrigin 
    S1 | A2 | Word | Printable document | 22-Jul-23  | InfoOrigin 
    S2 | A3 | XLS | Calculation document | 22-Jul-23  | InfoOrigin 
* Feature Files
    - Description should include
        1. Client Id from Client Table
        2. Sponsor Id from ClientSponsor Table
        3. Application Id from Application Table
        4. Feature Id from Feature Table
        On first execution of feature file, user should use ?? and code will generate unique featureID which will be used in  subseqent execution 
        5. Any details about this feature file
        
        Example:- 
        - First execution
        C1~S1~A1~??~Description of Feature
        - Subsequent execution C1~S1~A1~F1~Description of Feature
    - Scenario
        1. Description should include unique Test case number
        Example:
            - TC01, TC02, ....
        2. Data in Given/When/Then should be written in single quote(') not using double quote (")
* Cucumber 
    -  It should be configured to generate the .JSON file after execution summary
    
    Cypress | Selenium  
    --- | --- 
    package.json |@CucumberOptions  | 23  |  
    "json": { "enabled": true,"output": "cypress/cucumberReports/results.json"} | plugin = {json:target/cucumber-reports/CucumberRunnerTest.json"}   

                

* Python Code
    - Generated .JSON file should be placed in inboundJSONReports Directory
    - Execute the python code which will ingest data into mySQL or Postgres as per configuration
    - Upon successful ingestion all .JSON will be moved to processedJSONReports directory
* Power BI
    - Based on your role, access are available in dashboard of power BI using below URL