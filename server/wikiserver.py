import dbreader, dbconnect
import wikibard
import wikipedia
import random

# Change this if you'd like to use a local database or something
dbconfigname = 'local'

def removeTrailing(img_link):
    fmts = ['.jpg', '.png', '.tiff', '.gif', '.svg', '.bmp', '.jpeg']
    for fmt in fmts:
        if fmt in img_link:
            img_link = img_link[:img_link.find(fmt)+len(fmt)]
            break

def pageIDForPageTitle(title):
    dbconn = dbconnect.MySQLDatabaseConnection.connectionWithConfiguration(dbconfigname)
    pageID = dbreader.pageIDForPageTitle(dbconn, title)
    return pageID

def imagesForPageTitle(title):
    #just gotta sanitize the input
    title = title.replace("_", " ")
    page = wikipedia.page(title)
    if page:
        images = [x for x in page.images if not "Commons-logo" in x]
        images = [x for x in page.images if not ".svg" in x]
        # images = map(removeTrailing, images)
        images = sorted(images, key = lambda x: random.random())
        return images

def poemForPageTitle(title):
    dbconn = dbconnect.MySQLDatabaseConnection.connectionWithConfiguration(dbconfigname)
    dbconfig = dbconnect.MySQLDatabaseConnection.dbconfigForName(dbconfigname)
    pageID = dbreader.pageIDForPageTitle(dbconn, title)
    if pageID > 0:
        poem_lines = wikibard.poemForPageID(pageID, 'elizabethan', dbconfig, multi=True)
        wikibard.addTextToLines(dbconn, poem_lines)
        return "\n".join([line['text'] for line in poem_lines])
    else:
        return ""
