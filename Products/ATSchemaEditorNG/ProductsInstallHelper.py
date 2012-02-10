__revision__  = "$Revision: 47512 $"
__date__      = "$Date: 2007-08-17 19:40:22 +0200 (Fri, 17 Aug 2007) $"
__copyright__ = "Copyright (c) 2006 by banality agd"
__author__    = "Simon Pamies"
__full_info__ = "$Id: ProductsInstallHelper.py 602 2006-03-29 08:15:46Z zspamies $"
__licence__   = "see doc/licence.txt"

from StringIO import StringIO
from Products.Archetypes.public import listTypes
from Products.Archetypes.Extensions.utils import installTypes, install_subskin
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.Expression import Expression
from Products.CMFCore.ActionInformation import ActionInformation
from types import ListType, TupleType
from Acquisition import aq_base
import os, sys

try:
    blubb = True
except NameError:
    True  = 1
    False = 0

class ProductsInstallHelper:
    """ Class that simplifies the installation process of products """

    def __init__(self, productname, context):
        self._import_dir = ''
        self._stream = StringIO()
        self._productname = productname
        self._context = context
        self._root = self.getPortalObject() 

    # ***********************************
    # UTILITY FUNCTIONS
    # ***********************************
    
    def cleanUp(self):
        self.msg('Finished Installation of %s\nCleaning up...' % self._productname)
        return self.getStream().getvalue()

    def msg(self, message):
        print >> self._stream, message

    def error(self, message):
        print >> self._stream, '>> ERROR: %s' % message

    def exception(self, message):
        raise Exception, message

    def info(self, message):
        print >> self._stream, '>> INFO: %s' % message

    def getStream(self):
        return self._stream

    def getContext(self):
        return self._context

    def getProductName(self):
        return self._productname

    def getPortalObject(self):
        return getToolByName(self.getContext(), 'portal_url').getPortalObject()

    def getPortalProperties(self):
        return getToolByName(self.getContext(), 'portal_properties')
    
    def getHomeDir(self):
        """
        Returns the home directory of
        the Product given
        """
        
        return self._context.getPhysicalRoot().Control_Panel.Products[self._productname].home

    # ***********************************
    # TYPES AND SKINS
    # ***********************************
    
    def installSkins(self, globals=globals()):
        self.msg('Installing skin for %s' % self._productname)
        install_subskin(self._context, self.getStream(), globals)

    def installTypes(self):
        types = listTypes(self._productname)
        self.msg('Installing types')

        # helper message
        if not types:
            self.info('No Types found! Have you forgot to register some AT Class? (registerType(-classname-))')
            exit
        
        installTypes(self.getContext(), self.getStream(), types, self._productname)

    def installTypesSkin(self, globals):
        self.installSkins(globals)
        self.installTypes()
    
    def installTool(self, portalname, title):
        """ Install tool from Extensions/Install

                inst.installTool(config.TOOL_NAME, 'Antz Tool')
                # Antz Tool is the meta_type of the tool!

            You have to init tool in __init__.py:

                from AntzCave import AntzTool
                tools = (AntzTool,)
                
                utils.ToolInit(meta_type="Antz Tool",
                               tools=tools,
                               icon='tool.jpg',
                               ).initialize(context)

        """
        tt = getToolByName(self.getPortalObject(), portalname, None)
        if tt is None: # not installed yet
            addprod = self.getPortalObject().manage_addProduct[self.getProductName()]
            if not hasattr(addprod, 'manage_addTool'):
                self.error('You do not seem to have initialized the tool via CMFCore.utils.ToolInit in your __init__.py!')

            addTool = addprod.manage_addTool
            addTool(title)

            tt = getToolByName(self.getPortalObject(), portalname)
            at = getToolByName(self.getPortalObject(), 'portal_actions')
            at.addActionProvider(portalname)
            self.msg('Installed tool %s' % title)
        else:
            self.msg('Tool %s already installed!' % title)
        
    # ***********************************
    # DEPENDENCIES
    # ***********************************

    def installDependencies(self, dependencies):

        pqi = getToolByName(self.getContext(), 'portal_quickinstaller')
        for depend in dependencies:
            self.installProduct(depend)

    def installProduct(self, name):

        pqi = getToolByName(self.getContext(), 'portal_quickinstaller')
        if pqi.isProductInstalled(name):
            self.msg('%s is already installed - ignoring it' % name)
            return

        self.msg('Trying to install %s...' % name)

        try:
            pqi.installProduct(name)
            self.msg('Installed %s' % name)
            
        except:
            self.error('Could not install %s' % name)

    def uninstallProduct(self, products):

        pqi = getToolByName(self.getContext(), 'portal_quickinstaller')
        for pd in products:
            if not pqi.isProductInstalled(pd):
                self.msg('%s not installed - skipping uninstall request' % pd)
                continue

            else:
                try:
                    pqi.uninstallProducts([pd, ])
                    self.msg('Removed product %s' % pd)
                except Exception, e:
                    self.error('Could not uninstall %s (%s)' % (pd, str(e)))

    def checkDependencies(self, dependencies):
        """ Checks dependencies and raise Exception
        if product is not installed that should be """

        pqi = getToolByName(self.getContext(), 'portal_quickinstaller')
        for depend in dependencies:
            if not pqi.isProductInstalled(depend):
                raise Exception, 'Product %s not installed. MUST be installed before installing %s' % (depend, self._productname)
    
    # ***********************************
    # FTI (TYPES) HANDLING
    # ***********************************
    
    def getFTIForType(self, name):
        """ Returns the fti for the given named type """

        pti = getToolByName(self.getContext(), 'portal_types')
        return pti.getTypeInfo(name)
   
    def disableGlobalTypeIsAddable(self, name, disable=True):
        """ Disables the implicit addable feature of the given type.
        That leads to the fact that the type isn't anymore addable through
        types that do not explicitely allow addition of that type """

        fti = self.getFTIForType(name)

        if not fti:
            raise Exception, '%s seems not to be a valid type! \
                    Please control your Install.py and double check disableGlobalTypeIsAddable calls. \
                    It can also happen that you have to call this method after installTypesAndSkins.' % name
        
        if disable:
            self.msg('Disallowed implicit creation of %s' % name)
            fti._setPropValue('global_allow', 0)
        else: fti._setPropValue('global_allow', 1)
  
    def disableGlobalTypesAreAddable(self, namelist, disable=True):
        """ Disables a list of types """

        for item in namelist:
            self.disableGlobalTypeIsAddable(item, disable)

    # ***********************************
    # ACTION HANDLING
    # ***********************************

    def getActionsForType(self, type):
        """ Returns all actions defined for a specific type """

        tyt = getToolByName(self.getPortalObject(), 'portal_types')
        typeinfo = tyt.getTypeInfoFor(type)

        if typeinfo is not None:
            return typeinfo._cloneActions()
        
        return None

    def getActionsByProperties(self, **kw):
        """ Returns a list of actions from portal_actions matching kw """

        result = []
        pa = self.getPortalObject().portal_actions
        for action in pa._actions:
            count = 0
            for k,v in kw.items():
                if getattr(action, k, None):
                    count += 1

            if count == len(kw.keys()):
                result.append(action)

        return result

    def setActionCondition(self, action, conditionstring):
        """ Sets the condition for the given expression """

        action.condition = Expression(conditionstring)
        self.msg('Changed condition of action %s to %s' % (action.id, conditionstring))

    def setActionForType(self, type, actionid, **kw):
        """ Sets a field of the given action - dealing here with actions for types 
        Attributes must reside in **kw """

        tyt = getToolByName(self.getPortalObject(), 'portal_types')
        typeinfo = tyt.getTypeInfo(type)

        if typeinfo is not None:
            typeobj = getattr(tyt, typeinfo.getId())
            actions = typeinfo._cloneActions()
            
            for action in actions:
                if action.id == actionid:
                    for key in kw.keys():
                        self.msg('Changing attribute %s of action %s from type %s to %s' % (str(key), action.id, type, kw[key]))
                        setattr(action, key, kw[key])

            # saving changed actions
            typeobj._actions = tuple(actions)
   
    def createCompleteActionFor(self, object, id, title, 
            action, condition, permission, category, visible=1):
        """ Adds specified action to the object """

        if hasattr(object, 'addAction'):
            if object.getActionObject('%s/%s' % (category, id)) is None:
                object.addAction(id, title, 
                                 action, condition, permission, category, visible)
                self.msg('Added action %s to %s' % (title, object.getId()))

            else: self.info('Action %s on %s already installed' % (title, object.getId()))
        else: self.error('Could not add action %s to %s' % (title, object.getId()))
   
    # ***********************************
    # PERMISSIONS AND ROLES
    # ***********************************

    def ensurePermissionsToRole(self, name, permissions_list):
        pr = self.getPortalObject()
        self.ensurePermissionsToRoleFor(pr, name, permissions_list)

    def ensurePermissionsToRoleFor(self, object, name, permissions_list):
        object.manage_role(name, permissions_list)
        object._p_changed = 1
        self.msg('Registered specific permissions %s for role %s' % (','.join(permissions_list), name))

    def createPortalObjectRoles(self, roles):
        pr = self.getPortalObject()
        if type(roles) != type([]):
            roles = [roles]
            
        data = list(pr.__ac_roles__)
        for role in roles:
            if role not in data:
                data.append(role)
                
        pr.__ac_roles__ = tuple(data)
        self.msg('Added new roles: %s' % str(roles))

    def roleIsInstalled(self, role):
        pr = self.getPortalObject()
        return role in list(pr.__ac_roles__)

    def testForAccessOf(self, directory):
        fileobject = StringIO('tescht')
        try:
            filename = 'tescht_file_importer'
            here = self.getHomeDir()
            myfile = open(os.path.join(here, directory, filename), 'wb')

            fileobject.read()
            size = fileobject.tell()
            if size == 0:
                size = -1
            
            fileobject.seek(0)
            inpdata = fileobject.read(size)
            myfile.write(inpdata)
            myfile.close()
        
            self.msg('Directory %s seems to be clean!' % os.path.join(here, directory))
            os.unlink(os.path.join(here, directory, filename))

        except:
            fileobject.close()
            raise Exception, 'ATTENTION: Please adjust the rights of %s!!' % os.path.join(here, directory)

    def importXMLSecurityTo(self, object, filename):
        """ Imports the xml security to the given object """

        if hasattr(object, 'manage_importSecurity'):
            product_home = self.getHomeDir()
            import_dir = os.path.join(INSTANCE_HOME, 'import')
            xmlfile = open(os.path.join(product_home, 'import', filename), 'rb')

            object.manage_importSecurity(filename=xmlfile)
            self.msg('Imported XML Security from %s' % filename)

        else:
            self.error('Could not find xml import method! Security NOT imported!')

    # ***********************************
    # ZEXP HANDLING
    # ***********************************

    def importWorkflow(self, workflow_file):
        """
        Imports a new workflow from ZEXP
        file into the workflow tool. That
        file MUST reside in the import directory
        of the Product!
        """

        wf = getToolByName(self.getPortalObject(), 'portal_workflow')        
        self.importContentTo(wf, [workflow_file])
        self.msg('Imported new workflow: %s' % workflow_file)

    def importContentTo(self, object, filename_list, copy_to_import_dir=1):
        """
        Imports the given objects into the given object
        """

        self.msg('Importing %s' % filename_list)
        if copy_to_import_dir:
            self._beforeProductFileImport(self._context, self._productname, filename_list)

        for file in filename_list:
            try:
                object.manage_importObject(file)
                self.msg('Imported %s to %s' % (str(file), str(object))) 
            except Exception, e:
                self.error('Could not import %s.(%s)\n   Perhaps the content is already installed!' % (file, str(e)) )

            if copy_to_import_dir:
                self._afterProductFileImport(file)

    def _beforeProductFileImport(self, context, productname, filename_list):
        """
        Makes the given file importable by Zope.
        If all goes the right way we're returning true
        """
        
        for filename in filename_list:
            
            product_home = self.getHomeDir()
            import_dir = os.path.join(INSTANCE_HOME, 'import')
            src_file_bin = open(os.path.join(product_home, 'import', filename), 'rb')
            
            # if main import dir does not exists we create it
            if not os.path.exists(import_dir):
                os.makedir(import_dir)

            dest_file_bin = open(os.path.join(import_dir, filename), 'wb')
            dest_file_bin.write(src_file_bin.read())
            src_file_bin.close()
            dest_file_bin.close()

        return True

    def _afterProductFileImport(self, filename):
        """
        Removes all created files created by beforeProductFileImport
        """

        if self._import_dir:
            os.unlink(os.path.join(self._import_dir, filename))
 
    # ***********************************
    # WORKFLOW
    # ***********************************
    
    def assignWorkflowTo(self, portal_type, workflow_name, update=False):
        """
        Assigns the given workflow to the given
        portal_type. If <update> is given, then
        all objects are updated...
        """
        
        wf = getToolByName(self.getPortalObject(), 'portal_workflow')        
        wf.setChainForPortalTypes([portal_type], workflow_name)
        self.msg('Set new workflow %s for objects of type %s' % (workflow_name, portal_type))

        if update:
            wf.updateRoleMappings()
            self.msg('Updated all existing objects with new workflow definition')

    # ***********************************
    # REGISTERING OF MIMETYPES
    # ***********************************
    
    def registerFTPType(self, major, minor, portaltype):
        """
        Register a new content type for FTP/WebDAV Access
        Ex.: audio,mpeg,MP3File
        """

        self.msg('Registering new FTP/WebDAV type: %s/%s -> %s' % (major, minor, portaltype))
        ct = self._root.content_type_registry
        pid = '%s-%s-%s' % (major, minor, portaltype)
        ct.addPredicate(pid, 'major_minor')
        pred = ct.getPredicate(pid)
        pred.edit(major, minor)
        ct.assignTypeName(pid, portaltype)
        ct._p_changed = 1

    # ***********************************
    # MULTIPLE LANGUAGES
    # ***********************************
    
    def setupPloneLanguageTool(self, deflang='English', avail=['English']):
        """
        Settings for PloneLanguage Tool
        """

        po = self.getPortalObject()
        if hasattr(po, 'portal_languages'):
            pl = getattr(po, 'portal_languages')
            pl.manage_setLanguageSettings(deflang, avail, setRequestN=0)
            self.msg('Adapted PloneLanguageTool for specified languages')
            
        else: self.msg('Could not find PloneLanguageTool')
        
    def installPropertySheet(self, name, object, title=''):
        self.msg('Registering Property Sheet %s in portal_properties' % name)
        pp = self.getPortalProperties()
        if name in pp.objectIds():
            self.msg('Property Sheet already exists - Replacing it.')
            pp.manage_delObjects([name])

        if not object:
            self.error('PropertySheet is empty!!')
            
        else:
            try:
                pp.manage_addPropertySheet(name, title, object)
                self.msg('PropertySheet installed from %s' % str(object.__class__.__name__))
            except:
                self.error('Could not install the property sheet...')
    
    # ***********************************
    # PROPERTY EDITING
    # ***********************************

    def safeEditProperty(self, obj, key, value, data_type='string', empty_before=False, overwrite=True):
        """ An add or edit function """

        # deleting before adding
        if obj.hasProperty(key) and empty_before:
            obj._delProperty(key)
        
        # updating property
        if obj.hasProperty(key):
            if overwrite:
                obj._updateProperty(key, value)
                self.msg('Changed property %s to %s' % (key, value))

        # new one
        else:
            obj._setProperty(key, value, data_type)
            self.msg('Added property %s' % key)

    def addLinesToProperty(self, obj, key, values):
        if obj.hasProperty(key):
            data = getattr(obj, key)
            if type(data) is TupleType:
                data = list(data)

            # make sure we do not add things twice
            res = []
            for item in values:
                if item not in data:
                    res.append(item)

            values = res

            if type(values) is ListType:
                data.extend(values)

            else:
                data.append(values)
                
            self.msg('Updating property %s (value: %s) of %s' % (key, str(data), str(obj.Title())) )
            obj._updateProperty(key, data)
            
        else:
            self.msg('Adding property %s (value: %s) to %s' % (key, str(values), str(obj.Title())) )
            
            if type(values) is not ListType:
                values = [values]
                
            obj._setProperty(key, values, 'lines')

    def delLinesFromProperty(self, obj, key, values):
        if obj.hasProperty(key):
            data = getattr(obj, key)
            if type(data) is TupleType:
                data = list(data)

            res = []
            for item in data:
                if item not in values:
                    res.append(item)

            obj._delProperty(key)
            obj._setProperty(key, res, 'lines')
            self.msg('Removing lines from property %s: %s' % (key, values))

        else:
            self.error('Could not find property %s on %s scheduled for lines deletion!' % (key, str(obj.Title())) )

