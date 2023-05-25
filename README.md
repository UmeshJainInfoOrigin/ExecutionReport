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