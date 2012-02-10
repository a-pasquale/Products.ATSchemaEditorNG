# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: __init__.py 52127 2007-10-21 11:42:29Z naro $
"""

from Products.CMFCore.DirectoryView import registerDirectory
from config import SKINS_DIR, GLOBALS

registerDirectory(SKINS_DIR, GLOBALS)

# make refresh possible
from SchemaEditor import SchemaEditor
from ParentManagedSchema import ParentManagedSchema

import Products.CMFCore
from Products.Archetypes import process_types
from Products.Archetypes.public import listTypes
from config import *
from Products.CMFCore.permissions import AddPortalContent 

import patches

def initialize(context):

    # install ATSE Tool
    import SchemaEditorTool
    import ATSETemplateTool

    if INSTALL_DEMO_TYPES:
        import examples.content

    content_types, constructors, ftis = process_types(listTypes(PROJECT_NAME),
                                                      PROJECT_NAME)
    
    Products.CMFCore.utils.ContentInit(
        '%s Content' % PKG_NAME,
        content_types      = content_types,
        permission         = AddPortalContent,
        extra_constructors = constructors,
        fti                = ftis,
        ).initialize(context)
    
    tools = (SchemaEditorTool.SchemaEditorTool, ATSETemplateTool.ATSETemplateTool )
    Products.CMFCore.utils.ToolInit(meta_type=SchemaEditorTool.SchemaEditorTool.meta_type,
                                       tools=tools,
                                       icon='tool.jpg',
                                       ).initialize(context)

    Products.CMFCore.utils.ToolInit(meta_type=ATSETemplateTool.ATSETemplateTool.meta_type,
                                       tools=tools,
                                       icon='tool.jpg',
                                       ).initialize(context)
