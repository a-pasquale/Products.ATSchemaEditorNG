# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: SchemaEditorTool.py 47512 2007-08-17 17:40:22Z spamsch $
"""

from Globals import DTMLFile, InitializeClass
from AccessControl.SecurityInfo import ClassSecurityInfo
from Products.Archetypes.public import *

from SchemplateEditor import SchemplateEditor
from Products.CMFCore.utils import UniqueObject
from Products.CMFCore.ActionProviderBase import ActionProviderBase
from interfaces import ISchemaEditor

from config import TOOL2_NAME

class ATSETemplateTool(UniqueObject, ActionProviderBase, BaseFolder, SchemplateEditor):
    """ ATSE Template Tool """

    meta_type = portal_type = 'ATSchemaTemplateTool'
    id = TOOL2_NAME
    __implements__ = (ISchemaEditor,)

    manage_options = ( { 'label'  : 'Actions'
                       , 'action' : 'atse_schemplate_editor'
                       , 'help'   : ('CMFCore', 'Actions.stx')
                       }
                     ,
                     )

    actions = ({'id': 'editor_view',
            'name': 'Edit field definitions',
            'action': 'string:${object_url}/atse_schemplate_editor',
            'condition': "python:object.getId()=='%s'" % TOOL2_NAME,
            'permissions': ('Modify portal content',)
           },) 

    default_view='atse_schemplate_editor'
    schema = BaseContent.schema
    security = ClassSecurityInfo()
    icon = "sc_tool.jpg"

    def __init__(self):
        SchemplateEditor.atse_init(self)
        BaseFolder.__init__(self, TOOL2_NAME)
        self.setTitle('ATSE Template Editor')

registerType(ATSETemplateTool)

