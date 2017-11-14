#!/usr/bin/python

import sys
from oorpc import OpenObjectRPC
import getpass

def check_valid_argv(argv):
    if len(argv) != 4:
        print 'The arguments must be listed like this: host port database\nAborting ...'
        sys.exit(1)
    [host, port] = sys.argv[1:3]
    database_info = sys.argv[3]
    if ':' in database_info:
        (database, password) = database_info.split(':')
    else:
        database = database_info
        password = getpass.getpass('Password: ')
    username = 'admin'
    
    # [host, port, database, username, password]
    return (host, port, database, username, password)

def get_oorpc_from_argv(argv):
    [host, port, database, username, password] = check_valid_argv(argv)
    oorpc = OpenObjectRPC(host, database, username, password, port)
    return oorpc 
