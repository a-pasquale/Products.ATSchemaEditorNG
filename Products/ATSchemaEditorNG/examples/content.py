from Products.CMFCore.utils import getToolByName
from Products.Archetypes.public import *
from Products.ATContentTypes.content.document import ATDocument

from Products.ATSchemaEditorNG.ParentManagedSchema import ParentManagedSchema, ParentOrToolManagedSchema
from Products.ATSchemaEditorNG.SchemaEditor import SchemaEditor
from Products.ATSchemaEditorNG.config import ATSE_MANAGED_NONE, \
     ATSE_MANAGED_FULL
from Products.ATSchemaEditorNG import util

schema = BaseSchema.copy()

schema1= BaseSchema.copy() + Schema(( StringField('additionalField'), ))

schema3 = BaseSchema.copy() + Schema((
    StringField('atse_managed_full',
                atse_managed=ATSE_MANAGED_FULL,
                schemata='atse_manage_test',
                ),
    StringField('atse_managed_none',
                atse_managed=ATSE_MANAGED_NONE,
                schemata='atse_manage_test',
                ),
    StringField('atse_managed_none1',
                atse_managed=ATSE_MANAGED_NONE,
                schemata='atse_manage_test',
                ),
    ))

schema4 = BaseSchema.copy() + Schema((
    StringField('implicit',
                ),
    StringField('explicit_autocreate',
                accessor='getExplicit_autocreate',
                mutator='setExplicit_autocreate',
                ),
    StringField('explicit_def',
                accessor='getExplicit_def',
                mutator='setExplicit_def',
                ),
    ))


HAS_DATAGRID = True
try:
    from Products.DataGridField import DataGridField, DataGridWidget
    dgfield = DataGridField('test',
                widget=DataGridWidget(),
                columns=('col1', 'col2', 'col3'))
    schema4.addField(dgfield)

except ImportError:
    HAS_DATAGRID = False

class Container(SchemaEditor, BaseFolder):
    """
    Container to act as host for schema editing.
    """
    
    actions = ({'id': 'editor_view',
            'name': 'Schema Editor',
            'action': 'string:${object_url}/atse_editor',
            'permissions': ('Modify portal content',)
           },) 

    portal_type = "Container"
    def manage_afterAdd(self, item, container):
        """ """
        # do not show metadata fieldset
        self.atse_registerObject( Target1, ('metadata', ))
        #self.schema_editor_tool.atse_registerObject( Target1, ('metadata', ))
        BaseFolder.manage_afterAdd(self, item, container)

registerType(Container)

class Target1(ParentManagedSchema, BaseContent):
    """ Target content type to edit schema on """
    meta_type = portal_type = "Target1"
    schema = schema1

registerType(Target1)

class Target2(ParentManagedSchema, BaseContent):
    """ Target content type to edit schema on """
    meta_type = portal_type = "Target2"

registerType(Target2)

class Target3(ParentManagedSchema, BaseContent):
    """ Target content type to edit schema on """
    meta_type = portal_type = "Target3"
    schema = schema3

registerType(Target3)

class Target4(ParentManagedSchema, BaseContent):
    """ Target content type to edit schema on """
    meta_type = portal_type = "Target4"
    schema = schema4

    def manage_afterAdd(self, item, container):
        self.updateSchemaFromEditor()
        BaseContent.manage_afterAdd(self, item, container)
        self.accessor_called = False
        self.mutator_called = False

    def getExplicit_def(self):
        self.getField('explicit_def').get(self)
        self.accessor_called = True

    def setExplicit_def(self, value):
        self.getField('explicit_def').set(self, value)
        self.mutator_called = True

registerType(Target4)

class Target5(ParentOrToolManagedSchema, BaseContent):
    """ Content that is either parent or tool managed """

    meta_type = portal_type = 'Target5'
    schema = schema1

registerType(Target5)

class Collection(ParentManagedSchema, BaseContent):
    """ CT for a test """

    meta_type = portal_type = 'Collection'
    schema = schema1

    def manage_afterAdd(self, item, container):
        self.updateSchemaFromEditor()
        BaseContent.manage_afterAdd(self, item, container)

        specIds = [['specA%s'%b, 'genus%s'%b] for b in ['XY', 'XZ']]
        schema_id = item.portal_type

        # it can happen that the schema is not yet there
        # on first access
        if 'Collection' not in item.atse_getRegisteredSchemata():
            item.atse_registerSchema('Collection', self.schema)
            assert 'Collection' in item.atse_getRegisteredSchemata()

        mainSchema = item.atse_getSchemaById('Collection')
        schema_template = ''
        RESPONSE = None
        REQUEST = self.REQUEST

        abundanceFielddata = {
            'vocabulary':['None','Present','Common','Abundant','Bloom'],
            'default':'',
            'required':0,
            'createindex':0,
            'type':'StringField',
            'widget':'Select',
            'visible_edit':True,
            'visible_view':True
        }

        countFielddata = {
            'vocabulary': [(('None','None'),
                           ('Present','Present'),
                           ('Common','Common'),
                           ('Abundant','Abundant'),
                           ('Bloom','Bloom')),],
            'default': '',
            'label':' ',
            'required':0,
            'createindex': 0,
            'type':'IntegerField',
            'widget':'Integer',
            'widgetsize':6,
            'visible_edit':True,
            'visible_view':True
        }
    
        replace = str.replace
        for schemata in specIds:
            spec = replace(replace(schemata[0], ' ', '_'),'-','_')
            gen  = replace(replace(schemata[1], ' ', '_'),'-','_')

            # Add it first
            fielddata = {'schemata':gen}
            REQUEST.set('add_field', 'dummy')

            if not mainSchema.has_key('%sAbundance'%spec):
                REQUEST.set('name', '%sAbundance'%spec)
                abundanceFielddata.update({'schemata':gen, 'name':'%sAbundance'%spec, 'label':schemata[0]})
                SchemaEditor.atse_update(self.aq_parent.aq_inner, schema_id, schema_template, abundanceFielddata, REQUEST, RESPONSE)

                REQUEST.set('name', '%sCount'%spec)
                countFielddata.update({'schemata':gen, 'name':'%sCount'%spec})
                SchemaEditor.atse_update(self.aq_parent.aq_inner, schema_id, schema_template, countFielddata, REQUEST, RESPONSE) 

registerType(Collection)

class ObjectWithReferences(ParentManagedSchema, ATDocument):
    """ Object that holds references to other objects in relatedItems """

    meta_type = portal_type = 'ObjectWithReferences'
    archetype_name = 'ObjectWithRefs'
    schema = ATDocument.schema.copy()

registerType(ObjectWithReferences)
