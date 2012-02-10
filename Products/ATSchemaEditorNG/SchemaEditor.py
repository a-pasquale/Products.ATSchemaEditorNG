"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: SchemaEditor.py 113875 2010-03-24 08:32:51Z amleczko $
"""

__docformat__ = "epytext"
__license__ = "LGPL 2.1"

import re, os, urllib

from Globals import InitializeClass
from ExtensionClass import ExtensionClass
from AccessControl import ClassSecurityInfo
from Acquisition import ImplicitAcquisitionWrapper
from BTrees.OOBTree import OOBTree
from Products.CMFCore.PortalFolder import PortalFolder
from Products.CMFCore.permissions import *
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.public import DisplayList, BaseFolderSchema, Schema, FileField
from Products.Archetypes.utils import OrderedDict, shasattr
from Products.validation.config import validation
from Products.validation.validators import RegexValidator
from Products.statusmessages.interfaces import IStatusMessage
from ManagedSchema import ManagedSchema

from interfaces import ISchemaEditor

import util
from config import *
from util import LOG,INFO
import xml.dom.minidom

id_regex = re.compile('^[a-zA-Z][a-zA-Z0-9_]*[a-zA-Z0-9]$')
schemata_id_regex = re.compile('^[a-zA-Z][a-zA-Z0-9_ ]*[a-zA-Z0-9]$')
allowed = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/ ().,:;#+*=&%$�!'

# fields not to dump to xml and normal export
DONT_DUMP = ["_layers","__name__","widget","index_method","accessor","storage",
             "edit_accessor","mutator","generateMode","mode","validators",
             "referenceClass",]

def remove_unallowed_chars(s):
    return ''.join([c  for c in s  if c in allowed])

class SchemaEditorError(Exception): 
    
    def __init__(self, msg):
        """ Since exceptions can contain translated messages, they must be utf-8 encoded
        or error manager raises UnicodeDecodeError.
        """
        if type(msg) == type(u''):
            Exception.__init__(self, msg.encode('utf-8'))
        else:
            Exception.__init__(self, msg)
        

class SchemaEditor:
    """ a simple TTW editor for Archetypes schemas """

    security = ClassSecurityInfo()

    __implements__ = (ISchemaEditor,)

    atse_authUserHasRole = util._authenticatedUserHasRole

    security.declareProtected(ManageSchemaPermission, 'atse_init')
    def atse_init(self):
        self._clear(safe=True)
        self._initRegistries()

    def __setstate__(self, state):
        """ check for any initialization that hasn't happened, perform
            it if necessary """
        base_method = util._getBaseAttr(self, SchemaEditor, '__setstate__')
        if base_method is not None:
            base_method(self, state)

        self._clear(safe=True)
        self._initRegistries()

    def _migrateObjPtype(self):
        if not type(self._obj_ptype) == type([]):
            return
        ttool = getToolByName(self, 'portal_types')
        oobtree = OOBTree()
        if len(self._obj_ptype):
            tempFolder = PortalFolder('temp').__of__(self)
            tempFolder.unindexObject()
            for ptype in self._obj_ptype:
                fti = getattr(ttool, ptype)
                fti.constructInstance(tempFolder, ptype)
                obj = getattr(tempFolder, ptype)
                oobtree[ptype] = obj.__class__
            del tempFolder
        self._obj_ptype = oobtree

    def _clear(self, safe=False):
        if not safe:
            self._schemas = OOBTree()   # schema_id -> ManagedSchema instance
            self._obj_ptype = OOBTree() # portal type -> object class

        # safe update - not deleting contents
        else:
            if not shasattr(self, '_schemas'):
                self._schemas = OOBTree()
            if not shasattr(self, '_obj_ptype'):
                self._obj_ptype = OOBTree()
            elif type(self._obj_ptype) == type([]): # migrate to OOBTree
                self._migrateObjPtype()

    def _initRegistries(self, reinitialize=False):

        if not shasattr(self, '_widget_registry') or reinitialize is True:
            self._widget_registry = widget_registry.copy()
        if not shasattr(self, '_storage_registry') or reinitialize is True:
            self._storage_registry = storage_registry.copy()
        if not shasattr(self, '_field_registry') or \
               type(self._field_registry) == type(tuple()) or reinitialize is True:
            self._field_registry = field_registry.copy()

        # check for new format of registries and resync if necessary
        if not self._field_registry['StringField'].has_key('allowed_widgets'):
            self._field_registry = field_registry.copy()
            self._widget_registry = widget_registry.copy()

    security.declareProtected(ManageSchemaPermission, 'atse_reinitializeRegistries')
    def atse_reinitializeRegistries(self):
        """ If you have registered new widgets or fields then the registry is
        not automatically updated. You need to call this method on each instance
        of ATSE you want to have to updated registries. """

        self._initRegistries(reinitialize=True)
        return 'Registries updated!'

    security.declarePublic('atse_isTool')
    def atse_isTool(self):
        """ Returns true if instance is a tool """
        return self.getId() == TOOL_NAME

    security.declarePublic('atse_hasFeature')
    def atse_hasFeature(self, name):
        """ Returns true if the selected feature (look at config.py)
        is enabled.
        
        e.g: If you want to check for the annotation storage
        atse_hasFeature('ANNOTATION_STORAGE')
        
        @type name: String
        @param name: The feature name as mentioned in config w/o HAS_ prefix"""

        import config
        return getattr(config, 'HAS_%s' % name) and True or False

    # handy alias
    hasFeature = atse_hasFeature

    security.declareProtected(ManageSchemaPermission, 'atse_registerSchema')
    def atse_registerSchema(self, 
                            schema_id,
                            schema,     
                            filtered_schemas=(), 
                            undeleteable_fields=(), 
                            undeleteable_schematas=('default', 'metadata'), 
                            domain='plone'):
	""" Registers given schema with the editor
            
            @type schema_id: String
            @param schema_id: The name the schema will get in editor
            @type schema: C{Archetypes.Schema}
            @param schema: The schema object that should be registered
            @type filtered_schemas: Tuple
            @param filtered_schemas: Schemata that should not be listed in queries
            @type undeleteable_fields: Tuple
            @param undeleteable_fields: Names of fields that can not be deleted
            @type undeleteable_schematas: Tuple
            @param undeleteable_schematas: Names of schematas that can not be deleted
            @type domain: String
            @param domain: Translation domain to be used for this schema """

        # staying in sync
        self._clear(safe=True)
        self._initRegistries()
        
        if self._schemas.has_key(id):
            raise SchemaEditorError('Schema with id "%s" already exists' % id)
    
        S = ManagedSchema(schema.copy().fields())
        S._filtered_schemas = filtered_schemas
        S._undeleteable_fields = dict([[f, 0] for f in undeleteable_fields])
        S._undeleteable_schematas = dict([[s, 0] for s in undeleteable_schematas])
        S._i18n_domain = domain

        # make sure field gets default security settings
        for f in S.fields():

            # we can not rely on security defined on field
            # here because these are rights not roles. role
            # checking takes precedence over single rights (see __init__.py)
            self.atse_setFieldRightsForRole(f, 'UseFieldPermission', 'UseFieldPermission', 'Manager', 'Manager')
        
        self._schemas[schema_id] = S
        self._p_changed = 1

    security.declareProtected(ManageSchemaPermission, 'atse_registerPortalType')
    def atse_registerPortalType(self, ptype,
                                filtered_schemas=(), 
                                undeleteable_fields=(), 
                                undeleteable_schematas=('default', 'metadata'), 
                                domain='plone'):
        """ Register objects by portal type.
        
        @type ptype: String
        @param ptype: The portal type name (as listed in portal_types)
        @see: L{atse_registerSchema}
        """
        
        portal = getToolByName(self, 'portal_url').getPortalObject()
        tool = self
        if not self.atse_isTool():
            tool = getToolByName(portal, TOOL_NAME)

        try:
            tool.invokeFactory(type_name=ptype, id='atse-ptypedummy-%s' % ptype)
        except SchemaEditorError, e:
            if self.atse_isTool():
                raise Exception, 'You are trying to register an object for this tool that is not tool managed! (%s)' % e
            else:
                raise Exception, 'Object of type %s can not be managed by this schema editor! (%s)' % (ptype,e)
            
        ob = getattr(tool, 'atse-ptypedummy-%s' % ptype)
        if not shasattr(ob, 'isToolManaged'):
            raise Exception, 'Objects from this type can not be managed by ATSchemaEditor!'

        if self.atse_isTool() and not ob.isToolManaged:
            raise Exception, 'This type of objects can not be managed by this tool!'

        self.atse_registerObject(ob, filtered_schemas, undeleteable_fields, undeleteable_schematas, domain="plone")
        tool.manage_delObjects(['atse-ptypedummy-%s' % ptype, ])
        self._p_changed = 1
        
        return self._answer(dest='atse_editor', 
                            msg_id='atse_editing_schema_for_type', 
                            default='Now editing schema ${portal_type}',
                            translation_parameters={'portal_type':ptype},
                            schema_id=ptype)
                                        
    security.declareProtected(ManageSchemaPermission, 'atse_registerObject')
    def atse_registerObject(self, obj,
                            filtered_schemas=(), 
                            undeleteable_fields=(), 
                            undeleteable_schematas=('default', 'metadata'), 
                            domain='plone'):
        """
        Using that method you can register an object.
        Information needed are extracted from it. The Schema id
        is set to the portal type of the object.

        @type obj: object
        @param obj: The object from which schema should be extracted
        @see: L{atse_registerSchema}
        """
        if not hasattr(obj, 'portal_type'):
            raise Exception, 'Object %s is not an valid input' % str(obj)

        # avoiding update problems
        self._clear(safe=True)

        schema = getattr(obj, 'schema')
        ptype = getattr(obj, 'portal_type')

        if obj.__class__ == ExtensionClass:
            obj_klass = obj
        else:
            obj_klass = obj.__class__

        if not (self._obj_ptype.has_key(ptype)):
            self._obj_ptype[ptype] = obj_klass
        # do nothing if object is already there
        # XXX refresh schema
        else:
            return

        self.atse_registerSchema(ptype, schema,
                                 filtered_schemas,
                                 undeleteable_fields,
                                 undeleteable_schematas,
                                 domain)

    security.declareProtected(ManageSchemaPermission, 'atse_unregisterSchema')
    def atse_unregisterSchema(self, schema_id):
        """ Unregister schema 
        
        @type schema_id: String
        @param schema_id: The name of the schema that should be removed
        """

        if not self._schemas.has_key(schema_id):
            raise SchemaEditorError('No such schema: %s' % schema_id)
        del self._schemas[schema_id]
        try:
            del self._obj_ptype[schema_id]
        except: pass
        self._p_changed = 1

    security.declareProtected(ManageSchemaPermission, 'atse_reRegisterSchema')
    def atse_reRegisterSchema(self, schema_id, schema):
        """ Re-registering schema 
        
        @type schema_id: String
        @param schema_id: The name of the schema that should be re-registered.
        @type schema: C{Archetypes.Schema}
        @param schema: The schema object that should replace schema
        """

        self.atse_unregisterSchema(schema_id)
        self.atse_registerSchema(schema_id, schema)
        self._p_changed = 1
        
    security.declareProtected(ManageSchemaPermission, 'atse_reRegisterObject')
    def atse_reRegisterObject(self, object):
        """ Re-registering object 
        
        @type object: object
        @param object: The object that should be re-registered
        @see: L{atse_reRegisterSchema}
        """
        self.atse_unregisterSchema(object.portal_type)
        del self._obj_ptype[object.portal_type]
        self.atse_registerObject(object)
        self._p_changed = 1

    security.declareProtected(View, 'atse_getSchemaById')
    def atse_getSchemaById(self, schema_id):
        """ Return a schema by its schema_id 
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @raise SchemaEditorError: If there is no such schema
        @rtype: C{Archetypes.Schema}
        """
        if not self._schemas.has_key(schema_id):
            raise SchemaEditorError('No such schema: %s' % schema_id)
        return self._schemas[schema_id]

    security.declareProtected(View, 'atse_getRegisteredSchemata')
    def atse_getRegisteredSchemata(self):
        """ Returns all registered schemata

        @rtype: [String, ]
        """
        return self._schemas.keys()

    security.declareProtected(View, 'atse_selectRegisteredSchema')
    def atse_selectRegisteredSchema(self, schema_template, REQUEST=None, ptype=None):
        """ Redirection for selected schema. Should only
        be called for redirecting in html pages.

        @type schema_template: String
        @param schema_template: The name of the template to redirect to
        """
        req = REQUEST or self.REQUEST
        sel = ptype or req.form['selection']
    
        if req.form.get('unregister'):
            self.atse_unregisterSchema(sel)
                        
            self._answer(schema_template, 
                         msg_id='atse_editing_schema_for_type', 
                         default="Unregistered Schema ${portal_type}",                         
                         translation_parameters={'portal_type':sel},
                         schema_id=sel,)

        return self._answer(schema_template,
                            msg_id='atse_editing_schema_for_type',
                            default='Now editing schema for ${portal_type}',
                            translation_parameters={'portal_type':sel},
                            schema_id=sel,)

    security.declareProtected(View, 'atse_isSchemaRegistered')
    def atse_isSchemaRegistered(self, schema_id):
        """ Returns True if schema exists 
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @rtype: Bool
        """
        return self._schemas.has_key(schema_id) > 0

    security.declareProtected(View, 'atse_getDefaultSchema')
    def atse_getDefaultSchema(self):
        """ Returns the first schema in list. If there is no such one
        then the Archetypes base schema is returned.
        
        @rtype: C{Archetypes.Schema}
        """
        if self._schemas.items():
            return self._schemas.items()[0][1]

        return Schema()

    security.declareProtected(View, 'atse_getDefaultSchemaId')
    def atse_getDefaultSchemaId(self):
        """ Returns default schema id. Normally this will
        return the name of the first schema in the list. If
        there is no such on then an empty string is returned.

        @rtype: String
        """

        if self._schemas.items():
            return self._schemas.items()[0][0]

        return ''

    security.declareProtected(View, 'atse_getSchemataNames')
    def atse_getSchemataNames(self, schema_id, filter=True):
        """ Return names of all schematas for the given schema. Remember
        the difference between schema (the whole object containing all fields)
        and schemata (parts of a schema)
        
        @type schema_id: String
        @param schema_id: The name of the schema from which to extract schemata.
        @type filter: Bool
        @param filter: If set to True only unfiltered schematas are returned
        @rtype: [String, ]
        """

        if not schema_id:
            return ['',]

        S = self.atse_getSchemaById(schema_id)
        if filter:
            ret = []
            for n in S.getSchemataNames():
                if n in S._filtered_schemas or \
                   len(S.filterFields(schemata=n)) == \
                   len(S.filterFields(schemata=n, atse_managed=ATSE_MANAGED_NONE)):
                    pass
                else:
                    ret.append(n)
            return ret
        else:
            return [n for n in S.getSchemataNames()]

    security.declareProtected(View, 'atse_getSchemata')
    def atse_getSchemata(self, schema_id, name, filtered=True):
        """ Return a single schemata given by its name.
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @type name: String
        @param name: The name of the schemata
        @see: L{atse_getSchemataNames}
        @rtype: C{ATSchemaEditorNG.ManagedSchema}
        """
        S = self.atse_getSchemaById(schema_id)
        s = ManagedSchema()
        for f in S.getSchemataFields(name):
            if filtered and getattr(f,
                                    'atse_managed',
                                    ATSE_MANAGED_FULL) == ATSE_MANAGED_NONE:
                continue
            s.addField(f)
        return ImplicitAcquisitionWrapper(s, self)

    security.declareProtected(ManageSchemaPermission,
                              'atse_getUnmanagedFieldNames')
    def atse_getUnmanagedFieldNames(self, schema_id):
        """ Returns names of all fields that are not managed by
        the schema editor
        
        @type schema_id: String
        @param schema_id: The name of the schema from where to get fields
        @rtype: [String, ]
        """
        
        S = self.atse_getSchemaById(schema_id)
        pred = S._fieldIsUnmanaged
        return [f.getName() for f in S.filterFields(pred)]

    security.declareProtected(ManageSchemaPermission,
                              'atse_syncUnmanagedAndNewFields')
    def atse_syncUnmanagedAndNewFields(self, schema_id, schema_template=None,
                                       RESPONSE=None):
        """ synchronizes all unmanaged fields with the field
        definitions specified in the file system source code """
        unmanaged_fnames = self.atse_getUnmanagedFieldNames(schema_id)
        klass = self._obj_ptype[schema_id]
        src_schema = klass.schema
        atse_schema = self._schemas[schema_id]
        last_fname = ''
        for field in src_schema.fields():
            fname = field.getName()
            if not atse_schema.has_key(fname):
                atse_schema.addField(field)
            elif fname in unmanaged_fnames:
                atse_schema.replaceField(fname, src_schema[fname].copy())
            last_fname = fname
        self._schemas._p_changed = 1
        if schema_template is not None and RESPONSE is not None:
            
            self._answer(schema_template, 
                         msg_id='atse_fields_synced', 
                         default='Unmanaged and missing fields have been synchronized',
                         schema_id=schema_id)

    ######################################################################
    # global schema templates
    ######################################################################
    
    def atse_getSchemplateNames( self):
        """ Get the names of all available global schema templates 

        @rtype name: [String,]
        """
        atse_templates_tool = getToolByName(self, 'atse_template_tool')
        return atse_templates_tool.atse_schemplateList() 

    def atse_insertSchemplate(self, schema_id, schema_template, schemplate_id, RESPONSE=None):
        """ Insert a global schema template schemplate_id into the schema selected by schema_id
        
        @type schema_id: String
        @param schema_id: The name of the schema to where the schema template should be inserted
        @type schema_template: String
        @param schema_template: The tenmplate to redirect to in case of RESPONSE!=None
        @type name: String
        @param schemplate_id: The name of the schemata template to insert
        """
        
        atse_templates_tool = getToolByName(self, 'atse_template_tool')
        fields_to_add = atse_templates_tool.atse_getSchemplateById( schemplate_id).fields()
        
        S = self.atse_getSchemaById(schema_id )
        present_field_names = [p.getName() for p in S.fields()]

        for f in fields_to_add:
            if f.getName() in present_field_names:
                continue
            if hasattr(f, 'schemata'):
                if getattr(f, 'schemata') in SCHEMPLATE_IGNORE_SCHEMATA:
                    continue
            S.addField(f)

        self._schemas[schema_id] = S
        self._p_changed = 1

        if schema_template is not None and RESPONSE is not None:
            
            self._answer(schema_template, 
                          msg_id='atse_schema_template_inserted',
                          default='Schema Template inserted', 
                          schema_id=schema_id)


    ######################################################################
    # Add/remove schematas
    ######################################################################

    security.declareProtected(ManageSchemaPermission, 'atse_addSchemata')
    def atse_addSchemata(self, schema_id, schema_template, name, RESPONSE=None):
        """ Add a new schemata 
        
        @type schema_id: String
        @param schema_id: The name to where schemata should be added
        @type schema_template: String
        @param schema_template: The tenmplate to redirect to in case of RESPONSE!=None
        @type name: String
        @param name: The name of the schemata
        """
        S = self.atse_getSchemaById(schema_id)

        if not name:
            raise SchemaEditorError(self.translate('atse_empty_name', 
                                                   default='Empty ID given', 
                                                   domain='ATSchemaEditorNG'))

        if name in S.getSchemataNames():
            raise SchemaEditorError(self.translate('atse_exists', 
                                                   {'schemata':name},
                                                   default='Schemata \"$schemata\" already exists', 
                                                   domain='ATSchemaEditorNG'))
        if not schemata_id_regex.match(name):
            raise SchemaEditorError(self.translate('atse_invalid_id_for_schemata', 
                                                  {'schemata':name},
                                                  default='\"$schemata\" is an invalid ID for a schemata',
                                                  domain='ATSchemaEditorNG'))

        S.addSchemata(name)
        self._schemas[schema_id] = S
        self._p_changed = 1

        # add atseng permissions related attributes to new schema default field
        for field in S.fields():
            if hasattr(field, 'schemata') and field.schemata == name:
                self.atse_setFieldRightsForRole(field, 'UseFieldPermission', 'UseFieldPermission', 'Manager', 'Manager')

        if RESPONSE:
            self._answer(schema_template, msg_id='atse_added', 
                         default='Schemata added',
                         schemata=name,
                         schema_id=schema_id
                         )

    security.declareProtected(ManageSchemaPermission, 'atse_delSchemata')
    def atse_delSchemata(self, schema_id, schema_template, name, RESPONSE=None):
        """ Delete a schemata 
        
        @see: L{atse_addSchemata}
        """
        S = self.atse_getSchemaById(schema_id)

        if S._undeleteable_schematas.has_key(name): 
            raise SchemaEditorError(self.translate('atse_can_not_remove_schema', 
                                                   default='Can not remove this schema because it is protected from deletion',
                                                   domain='ATSchemaEditorNG'))
   
        if len(self.atse_getSchemataNames(schema_id, True)) == 1: 
            raise SchemaEditorError(self.translate('atse_can_not_remove_last_schema', 
                                                   default='Can not remove the last schema',
                                                   domain='ATSchemaEditorNG'))

        for field in S.getSchemataFields(name): 
            if S._undeleteable_fields.has_key(field.getName()):
                raise SchemaEditorError(self.translate('atse_schemata_contains_undeleteable_fields', 
                                        default='The schemata contains fields that can not be deleted',
                                        domain='ATSchemaEditorNG'))

        
        S.delSchemata(name)
        self._schemas[schema_id] = S
        self._p_changed = 1

        if RESPONSE:
            self._answer(schema_template,
                         msg_id='atse_deleted', 
                         default='Schemata deleted',                
                         schemata=self.atse_getSchemataNames(schema_id, True)[0],
                         schema_id=schema_id)

    ######################################################################
    # Field manipulation
    ######################################################################

    security.declareProtected(ManageSchemaPermission, 'atse_delField')
    def atse_delField(self, schema_id, schema_template, name, RESPONSE=None):
        """ Removes a field from the schema.
        
        @type schema_id: String
        @param schema_id: The name of the schema from where to remove field
        @type schema_template: String
        @param schema_template: The name of the template to redirect to
        @type name: String
        @param name: The name of the field to delete
        """

        S = self.atse_getSchemaById(schema_id)

        # security check
        fl = S[name]
        if S._undeleteable_fields.has_key(name) or not self.atse_userCanDelete(fl):
            raise SchemaEditorError(self.translate('atse_field_not_deleteable',
                                            {'name' : name},
                                            default='field \"$name\" can not be deleted because it is protected from deletion',
                                            domain='ATSchemaEditorNG'))

        old_schemata = S.get(name).schemata
        S.delField(name)  

        if old_schemata in S.getSchemataNames(): # Schematas disappear if they are empty
            return_schemata = old_schemata
        else:
            if len(self.atse_getSchemataNames(schema_id, True)) > 0:
                return_schemata = self.atse_getSchemataNames(schema_id, True)[0]
            else:
                return_schemata = ""

        self._schemas[schema_id] = S
        self._p_changed = 1
        
        if RESPONSE:
            self._answer( 
                          schema_template,
                          msg_id='atse_field_deleted',
                          default='Field deleted', 
                          schema_id=schema_id,
                          schemata=return_schemata)

    security.declareProtected(ManageSchemaPermission, 'atse_addField')
    def atse_addField(self, schema_id, schemata, schema_template,
                      name, RESPONSE=None):
        """ Create a new field for given schema and schemata.

        @type schema_id: String
        @param schema_id: The name of the schema from where to remove field
        @type schemata: String
        @param schemata: The name of the schemata the field should belong to
        @type schema_template: String
        @param schema_template: The name of the template to redirect to
        @type name: String
        @param name: The name of the field to delete 
        """
        
        S = self.atse_getSchemaById(schema_id)

        if not name:
            raise SchemaEditorError(self.translate('atse_empty_field_name', 
                                            default='Field name is empty',
                                            domain='ATSchemaEditorNG'))

        if not id_regex.match( name ):
            raise SchemaEditorError(self.translate('atse_not_a_valid_id', 
                                            {'id' : name},
                                            default='\"$id\" is not a valid ID',
                                            domain='ATSchemaEditorNG'))

        if name in [f.getName() for f in S.fields()]:
            raise SchemaEditorError(self.translate('atse_field_already_exists', 
                                           {'id' : name},
                                           default='\"$id\" already exists',
                                           domain='ATSchemaEditorNG'))

        fieldset = schemata    
        field = StringField(name, schemata=fieldset, widget=StringWidget)
        self.atse_setFieldRightsForRole(field, 'UseFieldPermission', 'UseFieldPermission', 'Manager', 'Manager')

        S.addField(field)
        self._schemas[schema_id] = S
        self._p_changed = 1

        if RESPONSE:        
            self._answer(schema_template,
                         msg_id='atse_field_added', 
                         default='Field added',                        
                         schema_id=schema_id,
                         schemata=fieldset, 
                         field=name)
        

    security.declareProtected(ManageSchemaPermission, 'atse_addOrReplaceField')
    def atse_addOrReplaceField(self, schema_id, name, fieldinstance):
        """ Adds or replaces the given field. You need to pass a complete
            field instance. This is the main difference to atse_addField where
            you pass a name and you get a string field.

            Example:
                myfield = schemaeditor.atse_getField('default', 'myfield')
                myfield.required = False
                schemaeditor.atse_addOrReplaceField('default', myfield)

            ATTENTION: This method does not perform any checks! 
        """

        S = self.atse_getSchemaById(schema_id)

        # set default permission
        if not hasattr(field, 'atse_field_view_right'):
            self.atse_setFieldRightsForRole(field, 'UseFieldPermission', 'UseFieldPermission', 'Manager', 'Manager')

        S[name] = fieldinstance
        self._schames[schema_id] = S
        self._p_changed = 1

    security.declareProtected(ManageSchemaPermission, 'atse_update')
    def atse_update(self, schema_id, schema_template, fielddata,
                    REQUEST, RESPONSE=None):
        """ Update a single field. Should only be used via atse_editor template. """
    
        S = self.atse_getSchemaById(schema_id)
        R = REQUEST.form
        FD = fielddata

        if R.has_key('add_field') or REQUEST.has_key('add_field'):
            self.atse_addField(schema_id, FD.get('schemata'), schema_template,
                               R.get('name', REQUEST.get('name')), RESPONSE)
            return            
        field_info = self._field_registry.get(FD.get('type'), None)
        if field_info is not None:
            field = field_info['field']
        else:
            msg = self.translate('atse_unknown_field', 
                                 {'field' : FD.get('type')},
                                 default='unknown field type: $field',
                                 domain='ATSchemaEditorNG')
            raise SchemaEditorError(msg) 

        D = {}    # dict to be passed to the field constructor
        D['default'] = FD.get('default', '')
        D['schemata'] = FD.get('schemata')
        D['searchable'] = FD.get('searchable', 0)
        storageMap = self.atse_getStorageMap()
        storageInfo = storageMap.get(FD.get('storage', 'None'), {})
        D['storage'] = storageInfo.get('storage', None)
        
        # set image field data
        if FD.get('type', '')=='ImageField':
            ms_w = str(FD.get('max_size_width'))
            ms_h = str(FD.get('max_size_height'))
            if ms_w.isdigit() and ms_h.isdigit():
                D['max_size'] = (int(ms_w), int(ms_h))
            sizes_v = FD.get('sizes', [])
            sizes = {}
            for size in sizes_v:
                try:
                    name, width, height = size.split()
                    if width.isdigit() and height.isdigit():
                        sizes[name] = (int(width), int(height))
                except ValueError:
                    continue
            D['sizes'] = sizes
            
        # call storage data processing method
        if storageInfo.has_key('post_method') and R.get('storage_data'):
            post_method = getattr(storageInfo['storage'],
                                  storageInfo['post_method'])
            post_method(context=self, 
                        public_name = FD.get('name'), 
                        storage_data = R.get('storage_data'))

        # build widget
        widget_data = self.atse_getWidgetMap().get(FD.get('widget', 'String'), None)
        if not widget_data:
            raise SchemaEditorError(self.translate('atse_unknown_widget', 
                                                  {'widget' : FD.get('widget')},
                                                  default='unknown widget type: $widget',
                                                  domain='ATSchemaEditorNG'))
        widget = widget_data['widget'].copy()

        # get properties for reference field
        D['relationship'] = FD.get('relationship', 'defaultRelation')

        if FD.has_key('vocabulary_display_path_bound'):
            D['vocabulary_display_path_bound'] = \
                FD.get('vocabulary_display_path_bound')

        if FD.has_key('multiValued'):
            D['multiValued'] = FD.get('multiValued')

        if FD.has_key('allowed_types'):
            allowed_types = []
            for c in FD.get('allowed_types').split(','):
                c = c.strip()
                if c: allowed_types.append(c)
            D['allowed_types'] = tuple(allowed_types)

        if FD.has_key('checkbox_bound'):
            widget.checkbox_bound = FD.get('checkbox_bound')

        # get startup_directory for ReferenceBrowserWidget
        if FD.has_key('startup_directory'):
            widget.startup_directory = FD.get('startup_directory')

        widget.size = FD.get('widgetsize', 60)
        widget.rows = FD.get('widgetrows', 5)
        widget.cols = FD.get('widgetcols', 60)
        maxlength =  FD.get('widgetmaxlength')
        if maxlength:
            widget.maxlength = maxlength

        # setting visibility of field
        widget.visible = {'edit' : 'visible', 'view' : 'visible'}
        if self.atse_hasFeature('FIELD_VISIBILITY_ENABLED'):
            if not FD.has_key('visible_edit'):
                widget.visible['edit'] = 'invisible'

            if not FD.has_key('visible_view'):
                widget.visible['view'] = 'invisible'

        if FD.has_key('description'):
            widget.description = FD['description']

        # Validators
        if not self.hasFeature('PARAMETRIZED_VALIDATOR_SUPPORT'):

            # create simple valdation chain based on tupled names
            if FD.has_key('validators'):
                if isinstance(FD['validators'], list):
                    validators = tuple(FD['validators'])
                else:
                    validators = tuple([v.strip() for v in FD['validators'].split(',')])

                if validators:
                    D['validators'] = validators
        
        else:

            # instantiate each validator using the parameter
            params_ = FD.get('validator_params', '').split('\r\n'); v_params = {}
            for item in params_:
                if item:
                    names, value = item.split('=')
                    validatorname, argname = names.split(':')
                    v_params.setdefault(validatorname, {}).update({argname:value})

            validators = []
            if isinstance(FD.get('validators', None), list):

                # we need to fetch defined validators
                # from service and then need to reinstantiate
                # each of them because we want to inject
                # paramaters
                for name in FD['validators']:
                    params = v_params.get(name)
                    if name != 'matchRegularExpression':
                        validator = validation.validatorFor(name)
                        if params:
                            newinstance = validator.__class__(name, **params)
                            validators.append(newinstance)

                        else: validators.append(validator)

                    else:
                        newinstance = RegexValidator('matchRegularExpression', params.get('regexp'))
                        validators.append(newinstance)

            if validators:
                D['validator_params'] = params_
                D['validators'] = tuple(validators)

        LOG('ATSchemaEditorNG', INFO, 'Creating field with validators %s' % str(validators))
        widget.label = FD.get('label')
        widget.label_msgid = 'label_' + FD.get('label')
        widget.i18n_domain = S._i18n_domain

        # support for dynfield conditions
        if self.atse_hasFeature('DYNFIELD'):
            widget.dyn_condition = FD.get('condition', None)

        D['widget'] = widget

        # build DisplayList instance for SelectionWidgets
        widget_map = self.atse_getWidgetMap()
        if widget_map[FD.get('widget')].get('useVocab'):
            vocab = FD.get('vocabulary', [])

            if len(vocab) == 1 and vocab[0].startswith('method:'):
                dummy,method = vocab[0].split(':')
                D['vocabulary'] = method

            elif len(vocab) == 1 and vocab[0].startswith('script:'):
		        # script name is computed in ManagedSchemaBase/vocabularyProxy
                D['vocabulary'] = 'vocabularyProxy'

            else:
                l = []
                for line in vocab:
                    line = line.strip()
                    if not line: continue
                    if '|' in line:
                        k,v = line.split('|', 1)
                    else:
                        k = v = line

                    k = remove_unallowed_chars(k)
                    l.append( (k,v))

                D['vocabulary'] = DisplayList(l)

        # support for vocabulary manager - settings made
        # here overwrite the settings from the list.
        if self.atse_hasFeature('VOCABULARY_MANAGER'):
            vocab = FD.get('managed_vocabulary', None)
            if vocab and vocab != '-':
                from Products.ATVocabularyManager.namedvocabulary import NamedVocabulary
                D['vocabulary'] = NamedVocabulary(vocab)

        D['required'] = FD.get('required', 0)
        
        LOG('ATSchemaEditorNG', INFO, 'Creating field with %s' % str(D))
        newfield = field(FD.get('name'), **D)
        
        # call custom data processing methods on fields
        if field_info.has_key('post_method'):
            post_method = getattr(self, field_info['post_method'], None)
            if post_method is not None:
                post_method(newfield, FD)
        
        if shasattr(self, '_post_method_name'):
            post_method = getattr(self, self._post_method_name)
            post_method(context=self,
                        field=newfield,
                        custom_data=R.get('custom_data'))

        # support for rights management specific to ATSE
        if self.atse_hasFeature('SECURITY_MANAGEMENT_ENABLED'):
            view_r = FD.get('view_role', ['UseFieldPermission', ])
            modify_r = FD.get('modify_role', ['UseFieldPermission', ])
            delete_r = FD.get('deletion_role', ['Manager', ])
            manage_r = FD.get('manage_role', ['Manager', ])
            self.atse_setFieldRightsForRole(newfield, view_r, modify_r, delete_r, manage_r)

        # support for field permission
        view_p = FD.get('view_permission', 'View')
        modify_p = FD.get('modify_permission', 'Modify portal content')
        newfield.read_permission = view_p
        newfield.write_permission = modify_p

        S.replaceField(FD.get('name'), newfield)
        self._schemas[schema_id] = S
        self._p_changed = 1

        self._answer(schema_template,
                     msg_id='atse_field_changed', 
                     default='Field changed', 
                      schema_id=schema_id,
                      schemata=FD.schemata, 
                      field=FD.name)

    security.declareProtected(ManageSchemaPermission, 'atse_setFieldRightsForRole')
    def atse_setFieldRightsForRole(self, fieldobject, view=None, modify=None, delete=None, manage=None):
        """ Sets rights for the given field.

        @type fieldobject: C{Archetypes.Field}
        @param fieldobject: The field object
        @type view: [String, ]
        @param view: A list of roles that can view this field
        @type modify: [String, ]
        @param modify: A list of roles that can modify this field
        @type delete: [String, ]
        @param delete: A list of roles that can delete this field in editor
        @type manage: [String, ]
        @param manage: A list of roles that can manage this field in editor
        """

        def _convertList(input):
            if type(input) != type([]):
                return [input, ]
            return input

        if view: fieldobject.atse_field_view_right = _convertList(view)
        if modify: fieldobject.atse_field_modify_right = _convertList(modify)
        if delete: fieldobject.atse_field_delete_right = _convertList(delete)
        if manage: fieldobject.atse_field_manage_right = _convertList(manage)
        
    security.declarePublic('atse_userCanDelete')
    def atse_userCanDelete(self, fieldobject):
        """ Returns True if current user can delete field. 
        
        @type fieldobject: C{Archetypes.Field}
        @param fieldobject: The field object
        @rtype: Bool
        """
        retv = util._authenticatedUserHasRole(self, 
                        getattr(fieldobject, 'atse_field_delete_right', 'Manager')) 
        if 'Anonymous' in fieldobject.atse_field_delete_right and \
                not util._authenticatedUserHasRole(self, 'Anonymous'):
                    return True
        return retv

    security.declarePublic('atse_userCanManageRights')
    def atse_userCanManageRights(self, fieldobject):
        """ Returns True if current user can manage field. 
        
        @type fieldobject: C{Archetypes.Field}
        @param fieldobject: The field object
        @rtype: Bool
        """
        retv = util._authenticatedUserHasRole(self, 
                        getattr(fieldobject, 'atse_field_manage_right', 'Manager')) 
        if 'Anonymous' in fieldobject.atse_field_delete_right and \
                not util._authenticatedUserHasRole(self, 'Anonymous'):
                    return True
        return retv

    security.declarePublic('atse_getPossibleViewPermissions')
    def atse_getPossibleViewPermissions(self, defvalue=['View', ]):
        """ Returns a list of possible permissions for the view permission.
        The values are saved in site_properties/atsePossibleViewPermissions. If
        there is no such property then it will return ['View', ]

        @rtype: List
        """

        props = getToolByName(self, 'portal_properties').site_properties
        if hasattr(props, 'atsePossibleViewPermissions'):
            return props.atsePossibleViewPermissions

        return defvalue
    
    security.declarePublic('atse_getPossibleModifyPermissions')
    def atse_getPossibleModifyPermissions(self, defvalue=['Modify portal content']):
        """ Returns a list of possible permissions for the modify permission.
        The values are saved in site_properties/atsePossibleModifyPermissions. If
        there is no such property then it will return ['Modify portal content', ]

        @rtype: List
        """

        props = getToolByName(self, 'portal_properties').site_properties
        if hasattr(props, 'atsePossibleModifyPermissions'):
            return props.atsePossibleModifyPermissions

        return defvalue
    
    security.declareProtected(ManageSchemaPermission, 'atse_computedFieldPostMethod')
    def atse_computedFieldPostMethod(self, field, field_data):
        """ Set the expression on the ComputedField.

        @see: C{Archetypes.ComputedField}
        """
        field.expression = field_data.get('expression', '')

    security.declarePublic('atse_getTextFieldContentTypes')
    def atse_getTextFieldContentTypes(self):
        """
	textfield_postmacro template needs to know list of supported content types
	"""
	return TEXT_FIELD_CONTENT_TYPES

    security.declareProtected(ManageSchemaPermission, 'atse_textFieldPostMethod')
    def atse_textFieldPostMethod(self, field, field_data):
        """
        set the field parameters on the TextField
        """
        field.allowable_content_types = field_data.get('allowable_content_types', [])
        field.default_content_type = field_data.get('default_content_type', 'text/plain')
        field.default_output_type = field_data.get('default_output_type', 'text/plain')

    security.declareProtected(ManageSchemaPermission, 'atse_attachFilePostMethod')
    def atse_attachFilePostMethod(self, field, fielddata):
        """ Associates a file to the given field """

        filedata = self.REQUEST.get('%s_file' % field.getName())

        # using Archetypes.FileField here and using current instance
        filefield = FileField('%s_file_internal' % field.getName())

        try:
            filefield.set(self, filedata)
        except ValueError: pass

    security.declareProtected(ManageSchemaPermission, 'atse_getAttachedFieldFileUnit')
    def atse_getAttachedFieldFileUnit(self, fieldname):
        """ Returns the associated archetypes filefield BaseUnit or None """

        filefield = FileField('%s_file_internal' % fieldname)
        return filefield.getBaseUnit(self)
	
    security.declareProtected(ManageSchemaPermission, 'atse_getAttachedFieldFile')
    def atse_getAttachedFieldFile(self, fieldname):
        """ Returns the associated archetypes filefield BaseUnit or None """

        filefield = FileField('%s_file_internal' % fieldname)
        return filefield
	
    security.declareProtected(ManageSchemaPermission, 'atse_dataGridFieldPostMethod')
    def atse_dataGridFieldPostMethod(self, field, field_data):
        """
        set-up DataGrid widget
        """
        columns = field_data.get('columns', [])
        widget = field.widget
        column_ids = []

        if isinstance(widget, DataGridWidget):
            for column in columns:
                column_def = column.split('|')

                if len(column_def)==2:
                    # widget.columns[column_id] = Column(column_title)
                    widget.columns[column_def[0]] = Column(column_def[1])
                    column_ids.append(column_def[0])

                elif len(column_def)==3:

                    # handling typed one
                    if column_def[-1].strip().startswith('('):
                        widget.columns[column_def[0]] = ValidatedColumn(column_def[1], column_def[2].strip('()'))
                        column_ids.append(column_def[0])

                    else:
                        # widget.columns[column_id] = SelectColumn(column_title, vocabulary_method)
                        widget.columns[column_def[0]] = SelectColumn(column_def[1], column_def[2])
                        column_ids.append(column_def[0])

            if column_ids:
                field.columns = tuple(column_ids)

    ######################################################################
    # Field / Widget / Storage registration handling
    ######################################################################

    # XXX integrate w/ AT's centralized field/widget registry in
    # Products.Archetypes.Registry
    security.declareProtected(ManageSchemaPermission, 'atse_getFieldTypes')
    def atse_getFieldTypes(self):
        """ Get this instance's list of registered field types. 
        
        @rtype: [String, ]
        """
        return self._field_registry.keys()

    security.declareProtected(ManageSchemaPermission, 'atse_getFieldMap')
    def atse_getFieldMap(self):
        """ Get this instance's registered field info. 
        
        @rtype: Dict
        """
        return self._field_registry

    security.declareProtected(ManageSchemaPermission, 'atse_registerFieldType')
    def atse_registerFieldType(self, field_id, field_klass, **kw):
        """Add a new field type to the set of registered field types;
        support keyword arguments:

        - visible: whether or not to include the field type in the schema
                   editor (default: True)

        - useStorage: whether or not field type has an AT storage component
                      (default: True)
                      
        - post_macro: path to a macro that will be injected at the end of the
                      field edit form
                      
        - post_method: method to call method(field, field_data) 
                       field_data contains all field_data.* fields.

        @type field_id: String
        @param field_id: The name of the field
        @type field_klass: C{Archetypes.Field}
        @param field_klass: The field object (unbound, class)
        """
        kw.update({'field': field_klass})
        self._field_registry[field_id] = kw
        self._p_changed = 1

    security.declareProtected(ManageSchemaPermission, 'atse_getWidgetInfo')
    def atse_getWidgetInfo(self, field=None):
        """ Get the instance's registered widget info or the default. If you
        pass in a field then it will only return widgets allowed for this field.
        
        @type field: C{Archetypes.Field}
        @param field: The field object for the acl check
        @rtype: [(name, widgetobject), ]
        """

        items = self._widget_registry.items(); result = []

        if field is None:
            return items

        else:
            for widget in items:
                if self.atse_isWidgetAllowedFor(widget[0], field):
                    result.append(widget)

        return result

    security.declareProtected(ManageSchemaPermission, 'atse_getWidgetMap')
    def atse_getWidgetMap(self):
        """ Get the instance's registered widget map or the default. 
        
        @rtype: Dict
        """
        return self._widget_registry

    security.declareProtected(ManageSchemaPermission, 'atse_registerWidget')
    def atse_registerWidget(self, widget_id, widget, **kw):
        """Add a new widget to the set of registered widgets; supported
        keyword arguments:

        - visible: whether or not to include the widget in the schema editor

        - useVocab: whether or not to include the key|value vocabulary box

        - size_macro: path to a macro that will accept the widget size data

        - post_macro: path to a macro that will be injected at the end of the
                      field edit form
                      
        @see: L{atse_registerFieldType}
        """
        kw['widget'] = widget
        self._widget_registry[widget_id] = kw
        self._p_changed = 1 # mutation might not trigger db write

    security.declareProtected(ManageSchemaPermission, 'atse_getStorageInfo')
    def atse_getStorageInfo(self):
        """ Get the instance's registered storage info or the default. 
        
        @rtype: [(name, storageobject), ]
        """
        return self._storage_registry.items()

    security.declareProtected(ManageSchemaPermission, 'atse_getStorageMap')
    def atse_getStorageMap(self):
        """ Get the instance's registered storage map or the default.
        
        @rtype: Dict
        """
        return self._storage_registry
        
    security.declareProtected(ManageSchemaPermission, 'atse_registerStorage')
    def atse_registerStorage(self, storage_id, storage, **kw):
        """ Add a new storage to the set of registered storages; supported
        keyword arguments:

        - visible: whether or not to include the storage in the schema editor

        - post_macro: path to a macro that will be injected at the end of the
                      field edit form
                      
        - post_method: method to call method(fieldName , storage_data) 
                       storage_data contains all storage_data.* fields.
        
        @see: L{atse_registerWidget}
        """
                      
        kw['storage'] = storage
        self._storage_registry[storage_id] = kw
        self._p_changed = 1 # mutation might not trigger db write
            
    ######################################################################
    # Editor-wide fieldeditor customization hooks
    ######################################################################

    security.declareProtected(ManageSchemaPermission, 'atse_setPostMacro')
    def atse_setPostMacro(self, post_macro_path, post_method_name):
        """ Specify a post_macro to use when rendering the fieldeditor
        interface for every field, regardless of field, widget, or storage
        type:

        @type post_macro_path: String
        @param post_macro_path: full path to the macro, starting with 'here',
                           e.g. '/here/your_template/macros/your_macro'

        @type post_method_name: String
        @param post_method_name: method to call method(context, field, custom_data)
                            custom_data contains all custom_data.* fields"""
        
        self._post_macro_path = post_macro_path
        self._post_method_name = post_method_name

    security.declareProtected(ManageSchemaPermission, 'atse_getPostMacro')
    def atse_getPostMacro(self):
        """ Return the editor-wide post macro path as a string.
        
        @rtype: String
        """
        return getattr(self, '_post_macro_path', '')

    security.declareProtected(ManageSchemaPermission, 'atse_setWidgetPostMacro')
    def atse_setWidgetPostMacro(self, widget_post_macro_path):
        """ Specify a post_macro to use when rendering the fieldeditor
        interface for every field, regardless of field, widget, or storage
        type; this macro will be rendered within the 'Widget settings'
        box in the field editor.  
        
        @type widget_post_macro_path: String
        @param widget_post_macro_path: Should be a full path to the macro, starting with 'here', e.g.
                                        '/here/your_template/macros/your_macro'
                                        
        """
        self._widget_post_macro_path = widet_post_macro_path

    security.declareProtected(ManageSchemaPermission, 'atse_getWidgetPostMacro')
    def atse_getWidgetPostMacro(self):
        """ Return the editor-wide widget post macro path as a string.
        
        @rtype: String
        """
        return getattr(self, '_widget_post_macro_path', '')

    ######################################################################
    # Moving schematas and fields
    ######################################################################

    security.declareProtected(ManageSchemaPermission, 'atse_schemataMoveLeft')
    def atse_schemataMoveLeft(self, schema_id, schema_template, name, RESPONSE=None):
        """ Move a schemata to the left.
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @type schema_template: String
        @param schema_template: The template to redirect to
        @type name: String
        @param name: The name of the schemata to move
        """
        S = self.atse_getSchemaById(schema_id)
        S.moveSchemata(name, -1)
        self._schemas[schema_id] = S
        self._p_changed = 1

        if RESPONSE:
            self._answeR(schema_template,
                      msg_id='atse_moved_left', 
                      default='Schemata moved to left',  
                      schema_id=schema_id,
                      schemata=name)

    security.declareProtected(ManageSchemaPermission, 'atse_schemataMoveRight')
    def atse_schemataMoveRight(self, schema_id, schema_template, name, RESPONSE=None):
        """ Move a schemata to the right
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @type schema_template: String
        @param schema_template: The template to redirect to
        @type name: String
        @param name: The name of the schemata to move
        """
        S = self.atse_getSchemaById(schema_id)
        S.moveSchemata(name, 1)
        self._schemas[schema_id] = S
        self._p_changed = 1

        if RESPONSE:
            self._answer(schema_template,
                      msg_id='atse_moved_right', 
                      default='Schemata moved to right',
                      domain='ATSchemaEditorNG', 
                      schema_id=schema_id,
                      schemata=name)

    security.declareProtected(ManageSchemaPermission, 'atse_fieldMoveLeft')
    def atse_fieldMoveLeft(self, schema_id, schema_template, name, RESPONSE=None):
        """ Move a field of a schemata to the left
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @type schema_template: String
        @param schema_template: The template to redirect to
        @type name: String
        @param name: The name of the field to move
        """
        S = self.atse_getSchemaById(schema_id)
        S.moveField(name, -1)
        self._schemas[schema_id] = S
        self._p_changed = 1

        if RESPONSE:
            self._answer(schema_template,
                      msg_id='atse_field_moved_up', 
                      default='Field moved up',                       
                      schemata=S[name].schemata, 
                      schema_id=schema_id,
                      field=name)

    security.declareProtected(ManageSchemaPermission, 'atse_fieldMoveRight')
    def atse_fieldMoveRight(self, schema_id, schema_template, name, RESPONSE=None):
        """ Move a field of a schemata to the right
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @type schema_template: String
        @param schema_template: The template to redirect to
        @type name: String
        @param name: The name of the field to move
        """
        S = self.atse_getSchemaById(schema_id)
        S.moveField(name, 1)
        self._schemas[schema_id] = S
        self._p_changed = 1

        if RESPONSE:
            self._answer(schema_template, 
                      msg_id='atse_field_moved_down', 
                      default='Field moved down', 
                      schemata=S[name].schemata, 
                      schema_id=schema_id,
                      field=name)

    security.declareProtected(ManageSchemaPermission, 'atse_changeSchemataForField')
    def atse_changeSchemataForField(self, schema_id, schema_template, name, schemata_name, RESPONSE=None):
        """ Move a field from the current fieldset to another one.
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @type schema_template: String
        @param schema_template: The template to redirect to
        @type name: String
        @param name: The name of the field to move
        @type schemata_name: String
        @param schemata_name: The target schemata
        """
        S = self.atse_getSchemaById(schema_id)
        S.changeSchemataForField(name, schemata_name)
        self._schemas[schema_id] = S
        self._p_changed = 1

        if RESPONSE:
            self._answer(schema_template,
                      msg_id='atse_field_moved', 
                      default='Field moved to other fieldset',                    
                      schemata=schemata_name, 
                      schema_id=schema_id,
                      field=name)

    ######################################################################
    # Hook for schema dumper
    ######################################################################

    security.declareProtected(ManageSchemaPermission, 'atse_dumpSchemata')
    def atse_dumpSchemata(self,schema_id, schemata_name):
        """ Dump schemata to python sourcecode.

        @type schema_id: String
        @param schema_id: The name of the schema
        @type schemata_name: String
        @param schemata_name: Name of the schemata to export
        @rtype: String
        """
        hasNewLine = re.compile("\n")        
        sch = self.atse_getSchemata(schema_id,schemata_name)
        schemaString = ""
        for sFields in sch.fields():
            schemaString += '\t%s("%s", \n' % (sch.atse_getFieldType(sFields), sFields.getName())
            for dFields in sFields.__dict__:
                if dFields not in DONT_DUMP:
                    if getattr(sFields,dFields):
                        schemaString += '\t\t%s =' % dFields   
                        fieldValue = getattr(sFields,dFields,'')
                        if isinstance(fieldValue,basestring):
                            schemaString += ' """%s""",\n' % fieldValue
                        else: 
                            schemaString += ' %s,\n' % str(fieldValue)                            
            schemaString += sch.atse_dumpWidget(sFields.widget)
            schemaString += "\t),\n"
            schemaString = re.sub("&quot;","&amp;quot;",schemaString)
            schemaString = re.sub("\<","&lt;",schemaString)
            schemaString = re.sub("\>","&gt;",schemaString)
        return schemaString

    security.declareProtected(ManageSchemaPermission, 'atse_dumpWidget')
    def atse_dumpWidget(self,widget):
        """ Dumps given widget to python sourcecode.

        @type widget: C{Archetype.Widget}
        @param widget: The widget object
        @rtype: String
        """
        hasNewLine = re.compile("\n")
        schemaString = ""
        schemaString += '\t\twidget=%s(\n' % widget.getName()
        
        for wFields in widget.__dict__:
            if getattr(widget,wFields):
                schemaString += "\t\t\t%s =" % wFields    
                fieldValue = getattr(widget,wFields,'')
                if isinstance(fieldValue,basestring):
                    schemaString += ' """%s""",\n' % fieldValue
                else: 
                    schemaString += ' %s,\n' % str(fieldValue)
        schemaString += "\t\t),\n"            
        return schemaString    

    security.declareProtected(ManageSchemaPermission, 'atse_dumpSchemataToXML')
    def atse_dumpSchemataToXML(self, schema_id, schemata_name):
        """ Dumps given schemata to xml

        @type schema_id: String
        @param schema_id: The name of the schema
        @type schemata_name: String
        @param schemata_name: Name of the schemata to export
        @rtype: String
        """
        if type(schemata_name) != type([]):
            schemata_name = [schemata_name, ]
        
        _schemata = ''
        for sS in schemata_name:
            schx = self.atse_getSchemata(schema_id, sS)
           
            _fields = ''
            for f in schx.fields():
                LOG('ATSchemaEditorNG', INFO, 'Exporting field %s' % f.getName())
                _field_props, fname = [], f.getName()
                _widget_props = []

                for prop in f.__dict__:
                    if prop not in DONT_DUMP:
                        fval = getattr(f, prop)
                        
                        # handle class attributes
                        if str(fval).find('<')>=0 and str(fval).find('>')>=0:
                            LOG('AnthillCMS', INFO, 'Found field %s that contains class ref and can not be handled by ATSE' % prop)
                            continue
                        
                        daval = str(fval).replace('<', '&lt;').replace('>', '&gt;')
                        _field_props += '      <%s>%s</%s>\n' % (prop, daval, prop)

                _field_props += '     <field_class_type>%s</field_class_type>\n' % f.__class__.__name__

                for wf in f.widget.__dict__:
                    wval = getattr(f.widget, wf)
                    daval = str(wval).replace('<', '&lt;').replace('>', '&gt;')
                    _widget_props += '        <%s>%s</%s>\n' % (wf, daval, wf) 

                _widget_props += '    <widget_class_type>%s</widget_class_type>\n' % f.widget.__class__.__name__
                            
                _fields = unicode(_fields)
                _fields += XML_FIELD % {'name':str(fname), 
                                       'properties':str(''.join(_field_props)).decode('utf8'),
                                       'widget': XML_WIDGET % {'properties':str(''.join(_widget_props)).decode('utf8')}}
            
            _schemata += XML_SCHEMATA % {'schemata': sS, 'fields': _fields} 

        _complete = XML_BODY % {'portal_type': schema_id, 'schemata': _schemata}
        return _complete

    security.declareProtected(ManageSchemaPermission, 'atse_dumpSchemaToXML')
    def atse_dumpSchemaToXML(self, schema_id):
        """ Dumps complete schema with all schematas included. This method
        should not be used directly.

        @type schema_id: String
        @param schema_id: The name of the schema
        @rtype: C{ATSchemaEditor.util.DownloadeableFileWrapper}
        """

        data = self.atse_dumpSchemataToXML(schema_id, self.atse_getSchemataNames(schema_id, False))
        wrapper = util.DownloadableFileWrapper(data, '%s-export.xml' % schema_id, 'text/plain')
        return wrapper(REQUEST=self.REQUEST)

    security.declareProtected(ManageSchemaPermission, 'atse_dumpSchemaToBackupFile')
    def atse_dumpSchemaToBackupFile(self, schema_template, schema_id, redirect=True):
        """ Saves schema to backup file. The name of the backup file
        is computed from path (set in site_properties), date and time
        
        @type schema_template: String
        @param schema_template: The name of the template to redirect to
        @type schema_id: String
        @param schema_id: The name of the schema to export
        @type redirect: Bool
        @param redirect: If set to true then a redirection (HTTP) is performed
        """
        
        data = self.atse_dumpSchemataToXML(schema_id, self.atse_getSchemataNames(schema_id, False))
        filepath = self.portal_properties.site_properties.atsePathToBackupFile

        # ensure slash
        filepath = filepath.rstrip('/') + '/'
        
        # make filepath unique
        import DateTime
        filepath = '%satse_%s_%s_%s.xml' % (filepath, 
                '-'.join(self.getPhysicalPath()[1:]), 
                str(self.toLocalizedTime(DateTime.DateTime(), True)).replace(' ', '-').replace(':', '-'),
                schema_id)
        
        f = open(filepath, 'wb')
        f.seek(0)
        f.write(data.encode('utf8'))
        f.flush()
        f.close()
        
        if redirect == True:
            self._answer(schema_template,
                         default='Exported schema %s to filesystem (file: %s)' % (schema_id, filepath),  
                         schema_id=schema_id,)

    security.declareProtected(ManageSchemaPermission, 'atse_doImportFileXML')
    def atse_doImportFileXML(self, schema_id, filename, REQUEST=None):
        """ Import XML file by filename """

        doc = xml.dom.minidom.parse(filename)
        return self.atse_doImportXMLDoc(schema_id, doc, REQUEST)

    security.declareProtected(ManageSchemaPermission, 'atse_doImportStringXML')
    def atse_doImportStringXML(self, schema_id, inputstring, REQUEST=None):
        """ Import XML string """

        doc = xml.dom.minidom.parseString(inputstring)
        return self.atse_doImportXMLDoc(schema_id, doc, REQUEST)

    security.declareProtected(ManageSchemaPermission, 'atse_doImportXMLDoc')
    def atse_doImportXMLDoc(self, schema_id, doc, REQUEST=None):
        """ Import XML file, replacing schema if existent. 
        
        @type schema_id: String
        @param schema_id: Name of the schema to replace
        @type doc: A DOM document
        @param filename: The DOM Document
        """

        schemata = doc.getElementsByTagName('schemata') 

        # load schema currently installed
        schema = Schema()
        if self.atse_isSchemaRegistered(schema_id):
            schema = self.atse_getSchemaById(schema_id)

            # first delete all fields
            for f in schema.fields():
                schema.delField(f.getName())

        def _getContentForNode(node):
            val = node.nodeValue or u''
            if not val:
                if node.childNodes:
                    for nd in node.childNodes:
                        if nd.nodeType == nd.TEXT_NODE:
                            val += nd.nodeValue

            # perform some conversion
            if val.startswith('{') or val.startswith('[') or val.startswith('(') \
                    or val.strip() in ['None', 'True', 'False']:
                val = 'val = %s' % val
                exec val

            else:
                # we have a string
                val = 'val = """%s"""' % val
                exec val

            return val

        for sS in schemata:
            sname = sS.getAttribute('name')
            fields = sS.getElementsByTagName('field')

            for field in fields:
                field_cls = _getContentForNode(field.getElementsByTagName('field_class_type')[0])
                field_name = _getContentForNode(field.getElementsByTagName('name')[0])

                # convert elements to properties
                xml_elm = [x for x in field.childNodes \
                        if getattr(x, 'tagName', 'NOT_INCLUDED') not in ['field_class_type', 'name', 'widget', 'NOT_INCLUDED']]

                field_props = {}
                for xl in xml_elm:
                    field_props[str(xl.tagName)] = _getContentForNode(xl)
                
                widget_props = {}
                wdg = field.getElementsByTagName('widget')[0]
                widget_cls = _getContentForNode(wdg.getElementsByTagName('widget_class_type')[0])

                for xl in wdg.childNodes:
                    if getattr(xl, 'tagName', 'widget_class_type') not in ['widget_class_type']:
                        widget_props[str(xl.tagName)] = _getContentForNode(xl)

                field_props['schemata'] = sname

                # creating widget
                exec "gw = %s(**widget_props)" % str(widget_cls)
                field_props['widget'] = gw
                exec "fl = %s(name='%s', **field_props)" % (str(field_cls), str(field_name))

                if getattr(fl, 'primary', False):
                    if schema.hasPrimary():
                        LOG('ATSchemaEditor', INFO, 'Warning: Importer found another primary field %s' % fl.getName())
                        fl.primary = False
                
                # always adding field because schema should be empty
                schema.addField(fl)
                LOG('ATSchemaEditorNG', INFO, 'Imported field %s' % field_name)

        self._schemas[schema_id] = schema 
        self._p_changed = 1

        if REQUEST:
            self._answer('atse_editor',
                         default='Imported schema for %s' % schema_id, schema_id=schema_id,)

    ######################################################################
    # Hook for UI
    ######################################################################

    security.declareProtected(ManageSchemaPermission, 'atse_getField')
    def atse_getField(self, schema_id, name):
        """ Return a field by its name 
        
        @type schema_id: String
        @param schema_id: The name of the schema
        @type name: String
        @param name: The name of the field
        """
        S = self.atse_getSchemaById(schema_id)
        return S[name]

    security.declareProtected(ManageSchemaPermission, 'atse_getFieldType')
    def atse_getFieldType(self, field):
        """ Return the type of a field 
       
        @type field: C{Archetypes.Field}
        @param field: A fieldobject
        @rtype: String
        """
        return field.__class__.__name__

    security.declareProtected(ManageSchemaPermission, 'atse_getFieldStorageName')
    def atse_getFieldStorageName(self, field):
        """ Return the current field storage name, if any.

        @type field: C{Archetypes.Field}
        @param field: A fieldobject
        @rtype: String
        """
        strg_name = None
        if getattr(field, 'getStorageName', None) is not None:
            try:
                strg_name = field.getStorageName(field)
            except AttributeError: # field has no storage
                pass
        return strg_name
    
    security.declareProtected(ManageSchemaPermission, 'atse_getFieldValidators')
    def atse_getFieldValidators(self, field):
        """ Return a list of the pertinent validators for a field.

        @type field: C{Archetypes.Field}
        @param field: A fieldobject
        @rtype: (String, )
        """
        validators = getattr(field, 'validators', ())
        # filtering out 'isEmpty..' validators since they get injected
        # into the validation chain automatically
        return tuple([v.name for v,q in validators if
                      not v.name.startswith('isEmpty')])

    security.declareProtected(ManageSchemaPermission, 'atse_formatVocabulary')
    def atse_formatVocabulary(self, field):
        """ Format the DisplayList of a field to be displayed within a textarea.

        @type field: C{Archetypes.Field}
        @param field: A fieldobject
        """

        vocabulary = field.vocabulary
        if isinstance(vocabulary, str):
            if vocabulary == 'vocabularyProxy':
                return 'script:'
            else:
                return 'method:' + vocabulary

        l = []
        if self.atse_hasFeature('VOCABULARY_MANAGER'):
            from Products.ATVocabularyManager.namedvocabulary import NamedVocabulary
            if isinstance(vocabulary, NamedVocabulary):
                return ''

        for k in vocabulary:
            v = vocabulary.getValue(k)
            if k == v: l.append(k)
            else: l.append('%s|%s' % (k,v))
        return '\n'.join(l)

    security.declareProtected(ManageSchemaPermission, 'atse_isNamedVocabularySelection')
    def atse_isNamedVocabularySelection(self, vocid, field):
        """ Checks that the given vocid is the fields current vocabulary """

        from Products.ATVocabularyManager.namedvocabulary import NamedVocabulary
        vocabulary = field.vocabulary
        if isinstance(vocabulary, NamedVocabulary):
            return vocid.lower() == vocabulary.vocab_name.lower()

        return False

    security.declareProtected(ManageSchemaPermission, 'atse_getVocabularyScriptName')
    def atse_getVocabularyScriptName(self, schema_id, field):
        """ Returns the script name of the vocabulary for the field """

        name = 'atse_%s_%sVocabulary' % (schema_id, field.getName())
        return name.replace(' ', '')

    security.declareProtected(ManageSchemaPermission, 'atse_schema_baseclass')
    def atse_schema_baseclass(self, schema_id):
        """ Return the name of baseclass of schema 
        
        @type schema_id: String
        @param schema_id: The name of the schema from where to extract baseclass
        @rtype: String
        """
        S = self.atse_getSchemaById(schema_id)
        return S.__class__.__name__

    security.declareProtected(ManageSchemaPermission, 'atse_getRegisteredValidatorNames')
    def atse_getRegisteredValidatorNames(self):
        """ Returns all registered validator names """

        lst = [kv for kv in validation.keys() if kv not in ['isEmpty', 'isEmptyNoError']]

        # we add a special case
        if self.atse_hasFeature('PARAMETRIZED_VALIDATOR_SUPPORT'):
            lst.append('matchRegularExpression')

        return lst

    security.declareProtected(ManageSchemaPermission, 'atse_isRegisteredValidatorName')
    def atse_isRegisteredValidatorName(self, name, field):
        """ Returns true if the given name is a validator for the given field """

        return name in [f[0].name for f in getattr(field, 'validators', [])]

    ######################################################################
    # [spamies] Helper methods for maintenance and widget access
    ######################################################################

    security.declarePublic('atse_isWidgetAllowedFor')
    def atse_isWidgetAllowedFor(self, widgetname, field):
        """ Returns True if the widget is allowed for the given field. Returns
        False if either the field is not in the registry or if there is no
        widget acl list defined.
        
        @type widget: String
        @param widget: The widget name as defined in config.widget_registry
        @type field: C{Archetypes.Field}
        @param field: The field that the widget is checked agains
        @rtype: Bool
        """

        wdg = self._field_registry.get(field.getType().split('.')[-1:][0], {}).get('allowed_widgets', [])
        if wdg:
            if widgetname in wdg: 
                return True

        return False

    security.declareProtected(ManageSchemaPermission, 'atse_isFieldVisible')
    def atse_isFieldVisible(self, fieldname, mode='view', schema_id=None):
        """ Returns True if the given field is visible in the given mode. Default is view.

        @type fieldname: String
        @param fieldname: The name of the field that should be checked
        @rtype: Bool
        """
        
        if not schema_id:
            schema_id = self.atse_getDefaultSchemaId()
            
        field = self.atse_getField(schema_id, fieldname)
        if hasattr(field.widget, 'visible'):
            visible = field.widget.visible
            if isinstance(visible, int):
                return visible
            if field.widget.visible.get(mode) == 'invisible':
                return False
            else: return True

        # always True if we've found nothing
        return True

    security.declareProtected(ManageSchemaPermission, 'atse_editorCanUpdate')
    def atse_editorCanUpdate(self, portal_type):
        """ Returns True if an object was registered and its portal_type could be saved.

        @type portal_type: String
        @param portal_type: The portal type
        @rtype: Bool
        """
        if hasattr(self, '_obj_ptype'):
            if portal_type and self._obj_ptype.has_key(portal_type):
                return True
        return False

    security.declareProtected(ManageSchemaPermission, 'atse_getToolManagedPortalTypes')
    def atse_getToolManagedPortalTypes(self):
        """ Returns a list of portal types that are tool managed """

        return self.portal_properties.site_properties.atseToolManagedTypes
    
    security.declareProtected(ManageSchemaPermission, 'atse_getParentManagedPortalTypes')
    def atse_getParentManagedPortalTypes(self):
        """ Returns a list of portal types that are tool managed """

        return self.portal_properties.site_properties.atseParentManagedTypes

    security.declareProtected(ManageSchemaPermission, 'atse_getManagedTypes')
    def atse_getManagedTypes(self):
        """ Returns a list of portal types that are managed """

        if self.atse_isTool():
            return self.atse_getToolManagedPortalTypes()
        return self.atse_getParentManagedPortalTypes()

    security.declareProtected(ManageSchemaPermission, 'atse_updateManagedSchema')
    def atse_updateManagedSchema(self,
                                 portal_type,
                                 schema_template,
                                 update_all=False,
                                 REQUEST=None, RESPONSE=None):        
        """ Update stored issue schema for all managed schemas.
            That can only done, if an complete object was registered.

            @type portal_type: String
            @param portal_type: Types that should be updated
            @type update_all: Bool
            @param update_all: Unless this is set to true only objects living under
                               this editor are updated (default)
        """
        # we absolutely need to have portal_type
        if not self.atse_editorCanUpdate(portal_type):
            return self._answer(schema_template,
                                msg_id='atse_unknown_portal_type',
                                translation_parameters={'portal_type':portal_type},
                                default='Can not determine portal_type of managed objects (${portal_type})...', 
                                )
                                 
        dobackup = self.portal_properties.site_properties.atseAutomaticBackupWhenUpdateSchema
        if dobackup == True:
            self.atse_dumpSchemaToBackupFile('atse_editor', portal_type, False)
                                 
        # we assume that the schema name is the same as the portal_type
        schema = self.atse_getSchemaById(portal_type)

        # gettin' objects and updating them - but only objects
        # starting at path where this editor is!

        selfpath = '/'.join(self.getPhysicalPath()[:-1])
        query = {}
        query['portal_type'] = portal_type
        if not update_all:
            query['path'] = selfpath 

        objects = [ o.getObject() for o in \
                    self.portal_catalog.searchResults(**query)]

        # ParentManagedSchema is refreshing the schema,
        # if the _v_ variable is None...
        fobjects = []
        for obj in objects:

            # do not update objects not managed by tool or vice versa
            if shasattr(obj, 'isToolManaged'):
                if getattr(obj, 'isToolManaged') != True and self.atse_isTool():
                    continue
                
                if getattr(obj, 'isToolManaged') == True and not self.atse_isTool():
                    continue

            if hasattr(obj, '_v_schema'):
                delattr(obj, '_v_schema')
                obj._p_changed = 1

            obj.__atse_should_update__ = True
            fobjects.append(obj.getId())
            LOG('ATSchemaEditorNG', INFO, 'Updated schema for %s' % '/'.join(obj.getPhysicalPath()))

        if RESPONSE:
            updt_objects = fobjects or ['NO objects updated!']
            
            return self._answer(schema_template,
                                msg_id='atse_objects_updated',
                                translation_parameters={'portal_type':portal_type},
                                default='Objects of type ${portal_type} updated successfully\nUpdated: %s' % '\n'.join(updt_objects), 
                                )
            

    security.declareProtected(ManageSchemaPermission,
                              'atse_syncUnmanagedAndNewFields')
    def atse_syncUnmanagedAndNewFields(self, schema_id, schema_template=None,
                                       RESPONSE=None):
        """ Synchronizes all unmanaged fields with the field
        definitions specified in the file system source code 
        XXX needs to be tested """
        unmanaged_fnames = self.atse_getUnmanagedFieldNames(schema_id)
        klass = self._obj_ptype[schema_id]
        src_schema = klass.schema
        atse_schema = self._schemas[schema_id]
        last_fname = ''
        for field in src_schema.fields():
            fname = field.getName()
            if not atse_schema.has_key(fname):
                atse_schema.addField(field)
                if last_fname:
                    atse_schema.moveField(fname, after=last_fname)
                else:
                    atse_schema.moveField(fname, pos='top')
            elif fname in unmanaged_fnames:
                atse_schema.replaceField(fname, src_schema[fname].copy())
            last_fname = fname
        self._schemas._p_changed = 1
        if schema_template is not None and RESPONSE is not None:
            self._answer(schema_template,
                         msg_id='atse_fields_synced',
                         default='Unmanaged and missing fields have been synchronized',
                         schema_id=schema_id)

    security.declareProtected(ManageSchemaPermission, 'atse_generateImageScaleList')
    def atse_generateImageScaleList(self, field):
        """ Generates content of the <textarea> for image scale list in the format scalename width height

        @type field: C{Archetypes.Field}
        @param field: The field object
        @rtype: String
        """
        result = ''
        if field.type=='image':
            sizes = getattr(field, 'sizes', {})
            for size,value in sizes.items():
                result += "%s %s %s\n" % (size, value[0], value[1])
        return result    
  
    security.declareProtected(ManageSchemaPermission, 'atse_generateDataGridColumnList')
    def atse_generateDataGridColumnList(self, field):
        """ Generates content of the <textarea> for datagrid columns definition

        @type field: C{Archetypes.Field}
        @param field: The field object
        @rtype: String
        """
        result = ''
        if field.type=='datagrid':
            columns = getattr(field.widget, 'columns', {})
            for column_id, column_def in columns.items():
                if isinstance(column_def, SelectColumn):
                    result += '%s|%s|%s\n' % (column_id, column_def.getLabel(self, field.widget), column_def.vocabulary)

                elif isinstance(column_def, ValidatedColumn):
                    result += '%s|%s|(%s)\n' % (column_id, column_def.getLabel(self, field.widget), column_def.getValidatorRaw())

                elif isinstance(column_def, Column):
                    result += '%s|%s\n' % (column_id, column_def.getLabel(self, field.widget))

            return result
        
    def _answer(self, dest, req=None, msg_id=None, default=None, translation_parameters={}, **kw):
        """ Helper function to generate UI responses for various schema editor functions.
        
        Renders Plone status message and redirects to a wanted page.
        
        @param dest: Target URL
        @param req: Zope request object or None to use context        
        @param msg_id: Translation id for the message
        @param default: Default message if no translation available,
        @param translation_parameters: Keywords for the translation message variable substitution
        @param kw: Additional keyword arguments to be added to URL
        """
        
        if req == None:
            req = self.REQUEST 
            
        if default:
            # First use code supplied message
            msg = default % translation_parameters

        if msg_id != None:
            # Try translation id if available
            msg = self.translate(msg_id,
                            translation_parameters, 
                            default=default, 
                            domain='ATSchemaEditorNG'
                            )
            
        
        if msg:
            # If we got status message, show it
            status = IStatusMessage(req)
            status.addStatusMessage(msg, type=u'info')
        
               
        url = dest + "?"                
        if kw:
            url += '&'.join(['%s=%s' % (k, urllib.quote(v)) for k,v in kw.items()])
        req.RESPONSE.redirect(url) 

InitializeClass(SchemaEditor)
