# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: interfaces.py 13696 2005-11-06 22:10:27Z spamsch $
"""

from util import LOG, INFO
from util import _authenticatedUserHasRole
from Products.Archetypes.utils import shasattr

def authRoleHasAccessFor(self, mode, instance=None):
    if self.hasRolesForMode(mode):
        rf = (mode in ('w', 'write', 'edit', 'set') and 'atse_field_modify_right') or 'atse_field_view_right'
        rl = getattr(self, rf)
        if rl:
            retv = self.atse_userHasSpecifiedRole(rl, instance, True)
            isanon = self.atse_userHasSpecifiedRole('Anonymous', instance, False)
            return ('Anonymous' in rl and not isanon) or retv

    return False

def hasRolesForMode(self, mode):
    dowrite = mode in ('w', 'write', 'edit', 'set')
    doread = mode in ('r', 'read', 'view', 'get')

    mok = None
    if dowrite: mok = getattr(self, 'atse_field_modify_right', [])
    if doread: mok = getattr(self, 'atse_field_view_right', [])

    if mok and 'UseFieldPermission' not in mok: 
        return True
    return False

# patching Field to also ask for role
def writeable(self, instance, debug=True):

    # @see: Field.py
    if 'w' not in self.mode:
        return False
  
    if self.hasRolesForMode('w'):
        return self.authRoleHasAccessFor('w', instance)

    return self._atse_old_writeable(instance, debug)

def readable(self, instance, debug=True):
    if self.hasRolesForMode('r'):
        return self.authRoleHasAccessFor('r', instance)

    # Reading is always allowed if no role specified
    return True

def readAndWriteable(self, instance, debug=True):
    if self.hasRolesForMode('r') and self.hasRolesForMode('w'):
        return self.authRoleHasAccessFor('r') and \
                self.authRoleHasAccessFor('w')

    # always True if not role based security
    return True

def checkPermission(self, mode, instance):
    if not self.hasRolesForMode(mode):
        return self._atse_old_checkPermission(mode, instance)
    
    return self.authRoleHasAccessFor(mode)

from Products.Archetypes.Field import Field
if not hasattr(Field, '_atse_old_checkPermission'):
    Field._atse_old_checkPermission = Field.checkPermission
    Field._atse_old_writeable = Field.writeable

Field.writeable = writeable
Field.checkPermission = checkPermission
Field.atse_readable = readable
Field.atse_readAndWriteable = readAndWriteable
Field.atse_userHasSpecifiedRole = _authenticatedUserHasRole
Field.authRoleHasAccessFor = authRoleHasAccessFor
Field.hasRolesForMode = hasRolesForMode

LOG('ATSchemaEditorNG', INFO, 'Patched Archetypes.Field to make role checking possible')

# patching RangeValidator that contains buggy code
def call(self, value, *args, **kwargs):
    if len(args)>=1:
        minval=args[0]
    else:
        minval=self.minval
        
    if len(args)>=2:
        maxval=args[1]
    else:
        maxval=self.maxval

    assert(minval <= maxval)
    try:
        nval = float(value)
    except ValueError:
        return ("Validation failed(%(name)s): could not convert '%(value)r' to number" %
                { 'name' : self.name, 'value': value})

    minval = float(minval)
    maxval = float(maxval)

    if minval <= nval <= maxval:
        return 1

    return ("Validation failed(%(name)s): '%(value)s' out of range(%(min)s, %(max)s)" %
            { 'name' : self.name, 'value': value, 'min' : minval, 'max' : maxval,})

from Products.validation.validators.RangeValidator import RangeValidator
RangeValidator.__call__ = call
LOG('ATSchemaEditorNG', INFO, 'Patched Products.validation.RangeValidator to relax max check and to fix string ranges')

