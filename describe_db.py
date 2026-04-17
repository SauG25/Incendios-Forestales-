import duckdb

con = duckdb.connect(database=r"data\BaseDeDatos_Working.db", read_only=True)

# Describe the database tables
tables = con.execute("SHOW TABLES").df()
print("Tables in the database:")
print(tables)

for table_name in tables['name']:
    print(f"\nSchema for table '{table_name}':")
    schema = con.execute(f"DESCRIBE {table_name}").df()
    print(schema)

con.close()