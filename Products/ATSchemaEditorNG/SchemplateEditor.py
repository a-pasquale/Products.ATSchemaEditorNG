# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG

License: see LICENSE.txt

$Id: TemplateEditor.py       2007-08-25 00:29:46Z mkoch $
"""

from Globals import InitializeClass 
from AccessControl import ClassSecurityInfo
from Products.Archetypes.public import BaseSchema
from Products.CMFCore.permissions import View
from SchemaEditor import SchemaEditor
from config import SCHEMPLATE_IGNORE_SCHEMATA, ManageSchemaPermission
import util

#from config import ATSE_MANAGED_FULL, ATSE_MANAGED_NONE

class SchemplateEditor(SchemaEditor):
    """ We wrap the SchemaEditor for special functionality case
        global template editing
    """

    security = ClassSecurityInfo()

    security.declareProtected(View, 'atse_getSchemplateById')
    def atse_getSchemplateById( self, atse_schemplate_id):
        """ Returns a schema template by id 
        
        @rtype C{ManagedSchema.ManagedSchema}
        """
        if not self._schemas.has_key( atse_schemplate_id):
            raise SchemaEditorError('No such schema template: %s' % atse_schemplate_id)
        else:
            return self.atse_getSchemaById( atse_schemplate_id)  
        
        return

    security.declareProtected(View, 'atse_schemplateList')
    def atse_schemplateList(self):
        """ Returns a list of all available schema templates 
        
        @rtype [String, ]
        """
        return self._schemas.keys()

    security.declareProtected(ManageSchemaPermission, 'atse_addSchemplate')
    def atse_addSchemplate(self, atse_schemplate_id, schema_template, RESPONSE=None):
        """ Adds a schema template.
        
        @type atse_schemplate_id: String
        @param atse_schemplate_id: The id of the schema template to be created
        @type schema_template: String
        @param schema_template: The name of the template to redirect to
        """

        S = BaseSchema.copy()

        if self._schemas.has_key( atse_schemplate_id ):
            raise SchemaEditorError('Schema template with id %s already exists' % schema_id)
        else:
            self.atse_registerSchema( 
                            atse_schemplate_id,
                            S,     
                            filtered_schemas=SCHEMPLATE_IGNORE_SCHEMATA)
                
        self._schemas._p_changed = 1
    
        if RESPONSE:        
            util.redirect(RESPONSE, schema_template,
                          self.translate('atse_schema_template_added', 
                                         default='Schema template added',
                                         domain='ATSchemaEditorNG'), 
                          schema_id=atse_schemplate_id)
        return 

    security.declareProtected(ManageSchemaPermission, 'atse_deleteSchemplateById')
    def atse_deleteSchemplateById(self, atse_schemplate_id, schema_template, RESPONSE=None):
        """ Deletes a schema template.
        
        @type atse_schemplate_id: String
        @param atse_schemplate_id: The id of the schema template to be deleted
        @type schema_template: String
        @param schema_template: The name of the template to redirect to
        """

        if not self._schemas.has_key( atse_schemplate_id):
            raise SchemaEditorError('No such schema template: %s' % atse_schemplate_id)
        else:
            self.atse_unregisterSchema( atse_schemplate_id)

        self._schemas._p_changed = 1
        
        if RESPONSE:        
            util.redirect(RESPONSE, schema_template,
                          self.translate('atse_schema_template_deleted', 
                                         default='Schema template deleted',
                                         domain='ATSchemaEditorNG')) 
        return            

InitializeClass(SchemplateEditor)
