import pandas as pd
import mysql.connector

config = {
  'user': 'root',
  'password': 'GondiaRice@441601',
  'host': '127.0.0.1',
  'database': 'test',
  'raise_on_warnings': True
}

cnx = mysql.connector.connect(**config)
# cursor = cnx.cursor()
# cursor.execute("select clientID, ClientName from client")
# for (clientID, ClientName) in cursor:
#   print("{}, {} was hired on ".format(
#     clientID, ClientName ))

# #cursor.close()
# cnx.close()


query = "select clientID, ClientName from client;"
result_dataFrame = pd.read_sql(query,cnx)
print(result_dataFrame)
cnx.close() #close the connection

print('test')