# -*- coding: iso-8859-15 -*-

"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: Install.py 52127 2007-10-21 11:42:29Z naro $
"""

from Products.ATSchemaEditorNG.config import *
from Products.ATSchemaEditorNG.ProductsInstallHelper import ProductsInstallHelper as Helper
from cStringIO import StringIO
from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.Extensions.utils import installTypes, install_subskin
from Products.ATSchemaEditorNG.config import GLOBALS, PROJECT_NAME, TOOL_NAME, TOOL2_NAME
from Products.CMFCore.utils import getToolByName

def install(self):                             
    inst = Helper('ATSchemaEditorNG', self)
    inst.installSkins(GLOBALS)
    inst.installTool(TOOL_NAME, 'ATSchemaEditorTool')
    inst.installTool(TOOL2_NAME, 'ATSchemaTemplateTool')
    inst.installTypes()

    # disable implicit addition of ATSE tool
    inst.disableGlobalTypeIsAddable('ATSchemaEditorTool')
    inst.disableGlobalTypeIsAddable('ATSchemaTemplateTool')

    # do not display SchemaEditor tool in the navtree
    ntp = getattr(self.portal_properties, 'navtree_properties', None)
    if ntp is not None:
        if ntp.hasProperty('metaTypesNotToList'):
             inst.addLinesToProperty(self.portal_properties.navtree_properties, 
                                     'metaTypesNotToList', 
                                     ['ATSchemaEditorTool','ATSchemaTemplateTool',])

    inst.safeEditProperty(self.portal_properties.site_properties, 
                            'atseNotManageablePortalTypes', 
                            ['Document', 'News Item', 'Event',
                             'ATSchemaEditorTool', 'ATSchemaTemplateTool', 'Folder', 'Image', 'File', 'Link', 'Topic', 'Favorite', 'Large Plone Folder'],
                            'lines', False, False)

    inst.safeEditProperty(self.portal_properties.site_properties,
                            'atsePathToBackupFile',
                            '/tmp/',
                            'string', False, False)
    
    inst.safeEditProperty(self.portal_properties.site_properties,
                            'atseAutomaticBackupWhenUpdateSchema',
                            False,
                            'boolean', False, False)
    
    inst.safeEditProperty(self.portal_properties.site_properties,
                            'atseToolManagedTypes',
                            ['Target5', ],
                            'lines', False, False)
    
    inst.safeEditProperty(self.portal_properties.site_properties,
                            'atseParentManagedTypes',
                            ['Target1', 'Target2', 'Target3'],
                            'lines', False, False)

    inst.safeEditProperty(self.portal_properties.site_properties,
                            'atsePossibleViewPermissions',
                            ['View', ],
                            'lines', False, False)

    inst.safeEditProperty(self.portal_properties.site_properties,
                            'atsePossibleModifyPermissions',
                            ['Modify portal content', ],
                            'lines', False, False)

    configlet = {
        'id': 'schema_editor_tool',
        'appId': PROJECT_NAME,
        'name': 'Schema editor',
        'action': 'string:$portal_url/schema_editor_tool/atse_editor',
        'category': 'Products',
        'permission': (ManagePortal,),
        'imageUrl': 'sc_tool.jpg',
    }

    self.portal_controlpanel.unregisterConfiglet(configlet['id'])
    try:
        self.portal_controlpanel.registerConfiglets((configlet,))
    except:
        inst.msg(traceback.print_exc())

    configlet2 = {
        'id': 'atse_template_tool',
        'appId': PROJECT_NAME,
        'name': 'ATSE template editor',
        'action': 'string:$portal_url/atse_template_tool/atse_schemplate_editor',
        'category': 'Products',
        'permission': (ManagePortal,),
        'imageUrl': 'sc_tool.jpg',
    }

    self.portal_controlpanel.unregisterConfiglet(configlet2['id'])
    try:
        self.portal_controlpanel.registerConfiglets((configlet2,))
    except:
        inst.msg(traceback.print_exc())

    return inst.cleanUp()

def uninstall(self):
    out = StringIO()

    # remove the configlet from the portal control panel
    configTool = getToolByName(self, 'portal_controlpanel', None)
    if configTool:
        configTool.unregisterConfiglet('schema_editor_tool')
        out.write('Removed ATSE configlet\n')
        configTool.unregisterConfiglet('atse_template__tool')
        out.write('Removed ATSE Template configlet\n')
    return out.getvalue()
