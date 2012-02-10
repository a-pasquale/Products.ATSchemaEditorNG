# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: util.py 66418 2008-06-10 00:41:32Z miohtama $
"""

import urllib
import types
import inspect
import logging
from md5 import md5
from ExtensionClass import ExtensionClass

INFO = 'InfoDummy'
log = logging.getLogger('ATSchemaEditorNG')

def LOG(title, level, message):
    """ Wrapper for zLOG """

    log.info(message)

def redirect(RESPONSE, dest, msg=None,**kw):
    """ redirect() helper method """
    
    if RESPONSE is not None:    
        url = dest + "?"
        if msg:
            log.warn("Using redirect() for messages is deprecated")
            
        if kw:
            url += '&'.join(['%s=%s' % (k, urllib.quote(v)) for k,v in kw.items()])
        RESPONSE.redirect(url) 

def create_signature(schema):
    """ Replacement for buggy signature impl in AT Schema """

    s = 'Schema: {'
    for f in schema.fields():

        s += '%s:%s.%s-%s.%s: {' % \
             (f.__name__,
              inspect.getmodule(f.__class__).__name__,
              f.__class__.__name__,
              inspect.getmodule(f.widget.__class__).__name__,
              f.widget.__class__.__name__)

        s += _property_extraction(f._properties)
        s += _property_extraction(f.widget.__dict__)
        s += '}'

    s = s + '}'
    return md5(s).digest()

def _property_extraction(properties):

    s = ''
    disallowed = [types.ClassType, types.MethodType, types.ModuleType, type(ExtensionClass)]

    sorted_keys = properties.keys()
    sorted_keys.sort()
            
    for k in sorted_keys:
        if (type(k) not in disallowed):
            if (type(properties[k]) not in disallowed):
                s = s + '%s:%s,' % (k, properties[k])

    return s


def _getBaseAttr(instance, klass, attr_name):
    """ traverses the base classes of the 'instance' object; returns the
        first class attribute 'attr_name' in a base class that is AFTER
        'klass' in the base class hierarchy.  useful for determining
        which superclass method to call from a mix-in class. """
    bases = instance.__class__.__bases__
    past = 0
    for base in bases:
        if past:
            if hasattr(base, attr_name):
                return getattr(base, attr_name)
        if base == klass:
            past = 1
    return None

def _authenticatedUserHasRole(caller, role, instance=None, shortcircuit=False):
    """ Returns true if current user has specified role """

    from AccessControl import getSecurityManager
    user = getSecurityManager().getUser()
    roles = user.getRoles()

    # short circuit if user is manager
    if shortcircuit == True and 'Manager' in roles:
        return True
   
    # look for inherited roles
    if instance:
        roles = user.getRolesInContext(instance)

    if isinstance(role, list):
        for r in role:
            if r in roles: return True

        return False

    return role in roles

class DownloadableFileWrapper:
    """wrapper object for access to sub objects
    - taken from Archetypes"""

    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, data, filename, mimetype):
        self._data = data
        self._filename = filename
        self._mimetype = mimetype

    def __call__(self, REQUEST=None, RESPONSE=None):
        if RESPONSE is None:
            RESPONSE = REQUEST.RESPONSE
        if RESPONSE is not None:
            mt = self._mimetype
            name =self._filename
            RESPONSE.setHeader('Content-type', str(mt))
            RESPONSE.setHeader('Content-Disposition',
                               'inline;filename=%s' % name)
            RESPONSE.setHeader('Content-Length', len(self._data))
        return self._data

