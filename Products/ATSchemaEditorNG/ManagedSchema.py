# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG

(C) 2003,2004, Andreas Jung, ZOPYX Software Development and Consulting
and Contributors
D-72070 Tübingen, Germany

Contact: andreas@andreas-jung.com

License: see LICENSE.txt

$Id: ManagedSchema.py 52127 2007-10-21 11:42:29Z naro $
"""

from Globals import InitializeClass 
from AccessControl import ClassSecurityInfo

from Products.Archetypes.public import ManagedSchema

from config import ATSE_MANAGED_FULL, ATSE_MANAGED_NONE

class ManagedSchema(ManagedSchema):
    """ We wrap the ManagedSchema class in case we need something
        special.
    """

    security = ClassSecurityInfo()

    def _fieldIsUnmanaged(self, field):
        if getattr(field,
                   'atse_managed',
                   ATSE_MANAGED_FULL) == ATSE_MANAGED_NONE or \
                   field.schemata in self._filtered_schemas:
            return 1

InitializeClass(ManagedSchema)
