# -*- encoding: utf-8 -*-
##############################################################################
#
#    Trobz - Open Source Solutions for the Enterprise	
#    Copyright (C) 2009 Trobz (<http://trobz.com>). All Rights Reserved
#
##############################################################################


"""
Wrapper for XML-RPC access to an OpenObject instance.


Introduces a small layer of abstraction encapsulating direct XML-RPC calls,
with 5 methods:
- create
- search
- read
- write
- delete
"""


import xmlrpclib
from optparse import OptionParser


def define_arg():
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-s", "--server", dest="server",
                  help="server name and (optionally) port. ex: localhost:8069")
    parser.add_option("-o", "--port", help="Port of server", dest="port")
    parser.add_option("-u", "--user", help="logged in user", dest="user", default='admin')
    parser.add_option("-p", "--password", help="password of logged in user", dest="password")
    parser.add_option("-d", "--database", help="database name", dest="database")
    (options, args) = parser.parse_args()
    
    return (options, args)

class OpenObjectRPC:
    """
    Wrapper for XML-RPC access to OpenObject
    """

    
    def __init__(self, host, dbname, username, password, port=8069):
        """
        Create and cache an XML-RPC connection to an instance of OpenObject
        """        
        self._password = password
        self._dbname = dbname
        sock_common = xmlrpclib.ServerProxy ('http://%s:%s/xmlrpc/common' % (host, port))
        self._uid = sock_common.login(dbname, username, password)
        self._sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (host, port))   

    
    def create(self, model, field_values):
        """
        Create a new instance for a model.
        
        - model: the OpenObject model
        - field_values: a dictionary of the fields of the record to be created
        - returns the id of the new instance
        """
        return self._sock.execute(self._dbname, self._uid, self._password, model, 'create', field_values)

    def search(self, model, criteria):
        """
        Search instances of a model based on a criteria.
        
        - model: the OpenObject model
        - criteria: a list of criterias, each of the criteria being a 3-tuple
          ([field name], [operator], [value]), where operator can be '=', '!=',...
        - returns the list of ids
        
        TODO:
        - see more possible operators
        
        Example: search('res.partner', [('name', '=', 'some name')])
        """
        return self._sock.execute(self._dbname, self._uid, self._password, model, 'search', criteria)

    def read(self, model, ids, fields):
        """
        Read one or several records from a model.
        
        - model: the OpenObject model
        - ids: a list of record ids, usually coming from a call to 'search'
        - fields: a list of the fields to be returned (all the fields are returned
          if this list is empty)
        - returns the list of instances, each instance being a dictionary
        
        Example: read('res.partner', [3, 6], ['name', 'city', 'country'])
        """
        return self._sock.execute(self._dbname, self._uid, self._password, model, 'read', ids, fields)

    def write(self, model, ids, field_values):
        """
        Updates one or several records from a model.
        
        - model: the OpenObject model
        - ids: a list of the record ids to update
        - field_values: a dictionay with the field values to write
        - returns the list of ids modified (TODO: confirm)
        
        TODO:
        - check the case of several ids in the list
        
        Example: TODO
        """
        return self._sock.execute(self._dbname, self._uid, self._password, model, 'write', ids, field_values)

    def delete(self, model, ids):
        """
        Delete one or several recordd from a model.
        
        - model: the OpenObject model
        - ids: a list of the record ids to update
        - return the list of ids deleted (TODO: confirm)
        """
        return self._sock.execute(self._dbname, self._uid, self._password, model, 'unlink', ids)

  
    def execute(self, model, method, *args):
        return self._sock.execute(self._dbname, self._uid, self._password, model, method, *args)
