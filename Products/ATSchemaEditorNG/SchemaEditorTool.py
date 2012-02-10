# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: SchemaEditorTool.py 53179 2007-11-05 17:59:28Z spamsch $
"""

from Globals import DTMLFile, InitializeClass
from AccessControl.SecurityInfo import ClassSecurityInfo
from Products.Archetypes.public import *

from SchemaEditor import SchemaEditor
from Products.CMFCore.utils import UniqueObject
from Products.CMFCore.ActionProviderBase import ActionProviderBase
from interfaces import ISchemaEditor

from config import TOOL_NAME

class SchemaEditorTool(UniqueObject, ActionProviderBase, BaseFolder, SchemaEditor):
    """ SchemaEditorTool"""

    meta_type = portal_type = 'ATSchemaEditorTool'
    id = TOOL_NAME
    __implements__ = (ISchemaEditor,)

    manage_options = ( { 'label'  : 'Actions'
                       , 'action' : 'atse_editor'
                       , 'help'   : ('CMFCore', 'Actions.stx')
                       }
                     ,
                     )

    actions = ({'id': 'editor_view',
            'name': 'Edit field definitions',
            'action': 'string:${object_url}/atse_editor',
            'condition': "python:object.getId()=='%s'" % TOOL_NAME,
            'permissions': ('Modify portal content',)
           },) 

    default_view='atse_editor'
    schema = BaseContent.schema
    security = ClassSecurityInfo()
    icon = "sc_tool.jpg"

    def __init__(self):
        SchemaEditor.atse_init(self)
        BaseFolder.__init__(self, TOOL_NAME)
        self.setTitle('Schema Editor')

registerType(SchemaEditorTool)

