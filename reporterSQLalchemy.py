import pandas as pd
from sqlalchemy import create_engine
import pymysql

user = 'root'
password= 'MyNewPass'
host= '127.0.0.1'
port=3306
database= 'test'
raise_on_warnings=True

def get_connection():
    return create_engine(
        url="mysql+pymysql://{0}:{1}@{2}:{3}/{4}".format(
            user, password, host, port, database
        )
    )

if __name__ == '__main__':
 
    try:
        # GET THE CONNECTION OBJECT (ENGINE) FOR THE DATABASE
        sqlEngine= get_connection()
        dbConnection= sqlEngine.connect()
        frame= pd.read_sql("select clientID, ClientName from client", dbConnection)
        pd.set_option('display.expand_frame_repr', False)
        print(frame)
        print(
            f"Connection to the {host} for user {user} created successfully.")
    except Exception as ex:
        print("Connection could not be made due to the following error: \n", ex)