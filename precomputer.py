import server.dbconnect as dbconnect
import server.dbreader as dbreader
import server.wikibard as wikibard
import mysql.connector
import argparse
import random
import copy
from multiprocessing import Process

parser = argparse.ArgumentParser(description="Precompute a shitload of wikipoems")
parser.add_argument('dbconfig', type=str, help="name of the database configuration in dbconfig.yml")
parser.add_argument('--processes', action='store', type=int, default=1, help="Number of separate processes to run")

args = parser.parse_args()
dbconfig_name = args.dbconfig

is_setup = False
top_dog_count = 1000
top_dogs = []
dbconfig = dbconnect.MySQLDatabaseConnection.dbconfigForName(dbconfig_name)

def setup():
    global top_dogs
    global is_setup
    conn = mysql.connector.connect(user=dbconfig['user'],
                                    password=dbconfig['password'],
                                    host=dbconfig['host'],
                                    database=dbconfig['database'])
    cursor = conn.cursor()
    query = (
        """SELECT view_counts.id FROM view_counts INNER JOIN page_categories"""
        """ ON page_categories.id = view_counts.id WHERE view_counts.count < 202917"""
        """ ORDER BY view_counts.count DESC LIMIT %s;"""
        )
    values = (top_dog_count, )
    cursor.execute(query, values)
    res = cursor.fetchall()
    top_dogs = [r[0] for r in res]
    is_setup = True
    conn.close()

def composeSlave(dbconfig, top_pages):
    while True:
        random.shuffle(top_pages)
        for page_id in top_pages:
            writeNewPoemForPage(dbconfig, page_id)

def writePoem(dbconfig, page_id, poem_id):
    ## Write the poem
    poem = wikibard.poemForPageID(page_id, 'elizabethan', dbconfig)
    print(poem)
    line_ids = [line['id'] for line in poem]

    ## Store the poem
    conn = mysql.connector.connect(user=dbconfig['user'],
                                    password=dbconfig['password'],
                                    host=dbconfig['host'],
                                    database=dbconfig['database'])
    cursor = conn.cursor()
    query = (
        """UPDATE cached_poems SET"""
        """ line_0=%s, line_1=%s, line_2=%s, line_3=%s,"""
        """ line_4=%s, line_5=%s, line_6=%s, line_7=%s,"""
        """ line_8=%s, line_9=%s, line_10=%s, line_11=%s,"""
        """ line_12=%s, line_13=%s, complete=1"""
        """ WHERE id=%s;"""
    )
    values = tuple(line_ids + [poem_id])
    cursor.execute(query, values)
    cursor.execute("""COMMIT;""")
    conn.close()

def writeNewPoemForPage(dbconfig, pageID=21):
    ## Create the row for the cached posStringForPoemLines
    write_conn = mysql.connector.connect(user=dbconfig['user'],
                                        password=dbconfig['password'],
                                        host=dbconfig['host'],
                                        database=dbconfig['database'])
    cursor = write_conn.cursor()
    query = """INSERT INTO cached_poems (page_id) VALUES (%s);"""
    values = (pageID,)
    cursor.execute(query, values)
    cursor.execute("""COMMIT;""");
    query = """SELECT LAST_INSERT_ID();"""
    cursor.execute(query)
    res = cursor.fetchall()
    poem_id = res[0][0]
    write_conn.close()

    ## Create the return dictionary
    d = {}
    d['complete'] = 0
    d['starting_page'] = pageID
    d['id'] = poem_id

    ## Write the poem
    writePoem(dbconfig, pageID, poem_id)

    return d

if __name__ == '__main__':
    setup()
    pool = []
    if args.processes>1:
        for i in range(args.processes):
            p = Process(target=composeSlave, args=(dbconfig, copy.deepcopy(top_dogs)))
            pool.append(p)
            p.start()
        try:
            for p in pool:
                p.join()
        except Exception as e:
            print e
            for p in pool:
                p.terminate()
    else:
        composeSlave(dbconfig, copy.deepcopy(top_dogs))