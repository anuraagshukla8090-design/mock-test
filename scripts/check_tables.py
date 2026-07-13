import psycopg2
conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="Nothing@123", dbname="questionbank")
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)
conn.close()
