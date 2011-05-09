# -*- coding: utf-8 -*-
'''Script that expires all feeds'''

import backend

def main():
    print 'Before:', backend.Post.query.count()
    for f in backend.Feed.query.all():
        print 'Expiring: ', f.xmlurl
        f.expire()
    print 'After:', backend.Post.query.count()

if __name__ == "__main__":
    backend.initDB()
    main()
