# -*- coding: iso-8859-1 -*-

"""
ATSchemaEditorNG
License: see LICENSE.txt
$Id: config.py 58028 2008-02-01 20:14:35Z spamsch $
"""

# Add your imports for fields and/or widgets
# you want to manage here
from Products.Archetypes.Field import *
from Products.Archetypes.Widget import *
from Products.Archetypes.Storage import *
from Products.Archetypes.Storage import MetadataStorage
from Products.Archetypes.utils import OrderedDict, shasattr

from util import LOG, INFO, log

## --------- Set the properties below to your needs ----------

# Should demo types be installed?
# !!! Must be set to true before running tests !!!
INSTALL_DEMO_TYPES = False

# Set this to false if you do not want the editor
# to show security related field settings
HAS_SECURITY_MANAGEMENT_ENABLED = True

# Set this to false if the UI should not allow
# setting of field visibility
HAS_FIELD_VISIBILITY_ENABLED = True

# Show extended text field information
# If set to false this will disable extended
# selection possibilities for text fields like
# content type selection or defaults.
HAS_EXTENDED_TEXTFIELD_CAPS = True

# Disable selection of storage selection
# Default: Attribute
HAS_STORAGE_SELECTION = False

# Setting that feature controls if you can work using
# parametrized validators. If this is set to True
# then you can write validators that request an
# additional parameter and this parameter is
# manageable via ATSE GUI. Please be aware that
# enabling this functionality patches the AT
# validation code and can lead to strange behaviour.
HAS_PARAMETRIZED_VALIDATOR_SUPPORT = True

# This feature controls if the editor UI shows
# management related functions like updating
# managed schemas or exporting schema.
HAS_MANAGEMENT_UI_FUNCTIONALITY = True

# Update mode
# True: Schema Editor changes are not persistent.
# The Schema of the object is kept in sync with
# the one defined on the filesystem.
# ATTENTION: Setting this property to True can
# lead to a complete data loss!!
# Never activate it on production systems
ALWAYS_SYNC_SCHEMA_FROM_DISC = False

## -------- internal definitions from here ----------

# constants used for the 'atse_managed' field attribute
ATSE_MANAGED_FULL = 1
ATSE_MANAGED_NONE = 0

SKINS_DIR = 'skins'
GLOBALS = globals()
PROJECT_NAME = PKG_NAME = 'ATSchemaEditorNG'
TOOL_NAME = 'schema_editor_tool'
TOOL2_NAME = 'atse_template_tool'
SCHEMPLATE_IGNORE_SCHEMATA = ['metadata', 'default']

# Permissions
ManageSchemaPermission = 'ATSE: Manage schema'

FIELD_REGISTRY_INFO = (
        ('StringField',      {'field': StringField, 'allowed_widgets':['String', 'Textarea', 'Richtext', 'Password', 'Select']}),
        ('IntegerField',     {'field': IntegerField, 'allowed_widgets':['Integer', 'Decimal', 'String']}),
        ('FloatField',       {'field': FloatField, 'allowed_widgets':['Decimal', 'String']}),
        ('TextField',        {'field': TextField, 'allowed_widgets':['Textarea', 'Richtext', 'Epoz'],
                              'post_macro': 'here/textfield_postmacro/macros/field_params',
                              'post_method': 'atse_textFieldPostMethod'}),
        ('FixedPointField',  {'field': FixedPointField, 'allowed_widgets':['Decimal', 'String']}),
        ('LinesField',       {'field': LinesField, 'allowed_widgets':['String', 'Lines', 'MultiSelect', 'MultiCheckbox', 'Select', 'Radio', 'Flex']}),
        ('DateTimeField',    {'field': DateTimeField, 'allowed_widgets':['Calendar', ]}),
        ('BooleanField',     {'field': BooleanField, 'allowed_widgets':['Boolean', ]}),
        ('ReferenceField',   {'field': ReferenceField, 'allowed_widgets':['InAndOut', ]}),
        ('ComputedField',    {'field': ComputedField, 'useStorage': False, 'allowed_widgets' : ['Computed', ],
                              'post_macro': 'here/computedfield_postmacro/macros/expression',
                              'post_method': 'atse_computedFieldPostMethod'}),
        ('ImageField',       {'field': ImageField, 'allowed_widgets':['Image', ]}),
    )

WIDGET_REGISTRY_INFO = (
    ('String',      {'widget':StringWidget(), 'visible':True, 'useVocab':False}),
    ('Textarea',    {'widget':TextAreaWidget(), 'visible':True, 'useVocab':False,
                     'size_macro':'here/atse_macros/macros/row_col_size'}),
    ('Radio',       {'widget':SelectionWidget(format='radio'), 'visible':True,
                     'useVocab':True}),
    ('Select',      {'widget':SelectionWidget(format='select'), 'visible':True,
                     'useVocab':True}),
    ('Flex',        {'widget':SelectionWidget(format='flex'), 'visible':True,
                     'useVocab':True, 'size_macro':'here/atse_macros/macros/row_col_size'}),
    ('Lines',       {'widget':LinesWidget(), 'visible':True, 'useVocab':False}),
    ('Calendar',    {'widget':CalendarWidget(), 'visible':True, 'useVocab':False}),
    ('Boolean',     {'widget':BooleanWidget(), 'visible':True, 'useVocab':False}),
    ('MultiSelect', {'widget':MultiSelectionWidget(), 'visible':True, 'useVocab':True}),
    ('MultiCheckbox',{'widget':MultiSelectionWidget(format='checkbox'), 'visible':True, 'useVocab':True}),
    ('Richtext',    {'widget':RichWidget(), 'visible':True, 'useVocab':False}),
    ('Id',          {'widget':IdWidget(), 'visible':True, 'useVocab':False}),
    ('Password',    {'widget':PasswordWidget(), 'visible':True, 'useVocab':False}),
    ('Visual',      {'widget':VisualWidget(), 'visible':True, 'useVocab':False}),
    ('Epoz',        {'widget':EpozWidget(), 'visible':True, 'useVocab':False}),
    ('Picklist',    {'widget':PicklistWidget(), 'visible':True, 'useVocab':True}),
    ('InAndOut',    {'widget':InAndOutWidget(), 'visible':True, 'useVocab':True}),
    ('Image',       {'widget':ImageWidget(), 'visible':True, 'useVocab':False,
                     'size_macro':'here/atse_macros/macros/image_scales'}),
    ('Integer',     {'widget':IntegerWidget(), 'visible':True, 'useVocab':False}),
    ('Decimal',     {'widget':DecimalWidget(), 'visible':True, 'useVocab':False}),
    ('Keywords',    {'widget':KeywordWidget(), 'visible':False, 'useVocab':False}),
    ('Reference',   {'widget':ReferenceWidget(), 'visible':True, 'useVocab':False}),
    ('Computed',    {'widget':ComputedWidget()}),
    )

STORAGE_REGISTRY_INFO = [
  ('Attribute', {'storage':AttributeStorage(), 'visible':True}),
  ('Metadata', {'storage':MetadataStorage(), 'visible':True}),
]

try:
    from Products.Archetypes.Storage.annotation import AnnotationStorage
    HAS_ANNOTATION_STORAGE = True
    log.info('Feature enabled: ANNOTATION_STORAGE')
except ImportError:
    HAS_ANNOTATION_STORAGE = False

if HAS_ANNOTATION_STORAGE:
    STORAGE_REGISTRY_INFO.append( ('Annotation', {'storage':AnnotationStorage(), 'visible':True}) )

# XML templates
XML_BODY = u"""<?xml version="1.0" encoding="utf-8"?>

<!-- Generated by ATSchemaEditorNG 0.4
     Copyright (c) 2004-2006 by Andreas Jung and Contributors
     Licence: LGPL
-->

<schema for="%(portal_type)s">
    %(schemata)s
</schema>
"""

XML_SCHEMATA = u"""
    <schemata name="%(schemata)s">
%(fields)s
    </schemata>
"""

XML_FIELD = u"""
    <field>
      <name>%(name)s</name>
%(properties)s %(widget)s
    </field>
"""

XML_WIDGET = u"""
    <widget>
%(properties)s
    </widget>
"""

TEXT_FIELD_CONTENT_TYPES = ( 'text/plain', 'text/html', )

# init routines for field,widget and storage management
field_registry = OrderedDict()
widget_registry = OrderedDict()
storage_registry = OrderedDict()

for k, v in FIELD_REGISTRY_INFO:
    field_registry[k] = v

for k, v in WIDGET_REGISTRY_INFO:
    widget_registry[k] = v

for k, v in STORAGE_REGISTRY_INFO:
    storage_registry[k] = v

# support for ATReferenceBrowserWidget
HAS_ATREF_WIDGET = False
try:
    from Products.ATReferenceBrowserWidget.ATReferenceBrowserWidget import ReferenceBrowserWidget
    widget_registry.update({'ReferenceBrowserWidget':
                            {'widget':ReferenceBrowserWidget(), 'visible':True}})

    field_registry.update({'ReferenceField':
                            {'field': ReferenceField, 'allowed_widgets':['InAndOut', 'ReferenceBrowserWidget']}})
    HAS_ATREF_WIDGET = True
    log.info('Feature enabled: ATREF_WIDGET')
except ImportError:
    pass

# support for DataGridField/Widget
HAS_DATAGRIDFIELD = False
try:
    from Products.DataGridField import DataGridField, DataGridWidget, Column, SelectColumn
    field_registry.update( {'DataGridField':
                            {'field': DataGridField, 'allowed_widgets':['DataGridWidget', ],
                             'post_method': 'atse_dataGridFieldPostMethod'}})
    
    widget_registry.update({'DataGridWidget':
                            {'widget': DataGridWidget(), 'visible':True,
                             'useVocab':False,
                             'size_macro':'here/datagridfield_macros/macros/columns'}})
    HAS_DATAGRIDFIELD = True
    log.info('Feature enabled: DATAGRIDFIELD')

    try:
        from Products.DataGridField import ValidatedColumn
    except ImportError:
        LOG('ATSchemaEditorNG', INFO, 'ATTENTION: Will not load DataGridField support! It seems that you do not have applied the patch found in doc/')
        raise

except ImportError:
    pass

# support for ATVocabularyManager
HAS_VOCABULARY_MANAGER = False
try:
    from Products import ATVocabularyManager
    HAS_VOCABULARY_MANAGER = True
    log.info('Feature enabled: VOCABULARY_MANAGER')
except ImportError:
    pass

# support for DynField
HAS_DYNFIELD = False
try:
    from Products import dynfield
    HAS_DYNFIELD = True
    log.info('Feature enabled: DYNFIELD')
except ImportError:
    pass

