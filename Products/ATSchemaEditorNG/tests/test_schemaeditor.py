#
#  ATSchemaEditorNG TestCase
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from ZPublisher.HTTPRequest import record

from atse_testcase import ATSETestCase
from Products.Archetypes.public import StringField, StringWidget
from Products.CMFCore.utils import getToolByName
from Products.ATSchemaEditorNG.config import TOOL_NAME

# import special users
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import nobody,system,User

from atse_testcase import makeContent

class NewStringField(StringField):
    pass

class NewStringWidget(StringWidget):
    pass

class TestSchemaEditor(ATSETestCase):

    def afterSetUp(self):
        self.installDependencies()
        self.createBasicSetup()

        self.container._clear()
        self.user_member = User('testmember', '', ('Member', ), []).__of__(self.portal.acl_users)
        self.user_manager = User('testmanager', '', ('Manager', ), []).__of__(self.portal.acl_users)
        self.user_anonymous = nobody.__of__(self.portal.acl_users)

        self.container.atse_registerObject(self.target1)

    def testObjectWithReferences(self):
        self.container.atse_registerPortalType('ObjectWithReferences')
        self.failUnless('refobject' in self.container.objectIds())

        self.container.refobject.setRelatedItems(self.container.target4.UID())
        self.failUnless(len(self.container.refobject.getRelatedItems()) == 1)

        # all seems to go well until we try to edit this object with refs set
        self.failUnless(Exception, self.container.refobject.base_edit())

    def testCreateObjectByDoCreate(self):
        factory = getToolByName(self.portal, 'portal_factory')
        factoryTypes = oldFC = factory.getFactoryTypes().keys()
        factoryTypes.extend(['Target4', 'Target5'])
        factory.manage_setPortalFactoryTypes(listOfTypeIds=factoryTypes)
        temp_object = self.container.restrictedTraverse('portal_factory/Target4/tmp_id')
        foo = temp_object.portal_factory.doCreate(temp_object, 'foo')
        self.failUnless('foo' in self.container.objectIds())

    def test_objectCreationAfterEditorUpdate(self):
        self.container.atse_registerPortalType('Target4')
        self.container.atse_addField('Target4', 'default', None, 'testfieldname', None)
        self.container.invokeFactory(id='datarget', type_name='Target4')
        ct = getattr(self.container, 'datarget')
        self.failUnless(ct.Schema().get('testfieldname', None) != None)

    def test_ToolAndToolManagedSchemas(self):
        self.failUnless(getToolByName(self.portal, TOOL_NAME))
        tl = getToolByName(self.portal, TOOL_NAME)
        tl._clear()
        tl.atse_registerPortalType('Target5')
        self.failUnlessRaises(Exception, tl.atse_registerPortalType, 'Target1')
        tl.atse_addField('Target5', 'default', None, 'testfieldnew', None)
        
        newSecurityManager(self.container.REQUEST, self.user_manager)
        self.failUnless(tl.atse_userCanDelete(tl.atse_getField('Target5', 'testfieldnew')))

    def testPortalFactoryBasedCreationForParentManagedSchema(self):
        """ We want to test types created by portal_factory """
        
        factory = getToolByName(self.portal, 'portal_factory')
        factoryTypes = oldFC = factory.getFactoryTypes().keys()
        factoryTypes.extend(['Target4', 'Target5'])
        factory.manage_setPortalFactoryTypes(listOfTypeIds=factoryTypes)
        self.container.invokeFactory(id='target4-factory', type_name='Target4') 
        newob = self.container.restrictedTraverse('portal_factory/target4-factory')
        self.failUnless(newob.getId() == 'target4-factory')

        # Target4 is parent managed so parent needs to be acquired if object
        # is in portal_factory. The following call fails if there is
        # no support for portal_factory in ParentManagedSchema
        schema = newob.Schema() 

        # now test ParentOrToolManagedSchema
        self.failUnless(getToolByName(self.portal, TOOL_NAME))
        tl = getToolByName(self.portal, TOOL_NAME)
        tl._clear()
        self.container.invokeFactory(id='target5-factory', type_name='Target5')
        newob5 = self.container.restrictedTraverse('portal_factory/target5-factory')
        self.failUnless(newob5.aq_parent.__class__.__name__ == 'FactoryTool')
        tl.atse_registerPortalType('Target5')

        provider = newob5.lookup_provider()
        self.failIf(provider.getId() == TOOL_NAME)
        schema5 = newob5.Schema()
        self.failUnless(provider.getId() == self.container.getId())

        factory.manage_setPortalFactoryTypes(listOfTypeIds=oldFC)

    def test_PortalTypeRegistration(self):
        self.container._clear()
        newSecurityManager(self.container.REQUEST, self.user_manager)
        self.container.atse_registerPortalType('Target1')
        self.failUnless('Target1' in self.container.atse_getRegisteredSchemata())
        self.container.atse_registerPortalType('Target3')
        self.failUnless('Target3' in self.container.atse_getRegisteredSchemata())

    def test_XMLExportImport(self):
        self.container._clear()
        self.container.atse_registerPortalType('Target1')
        dstr = self.container.atse_dumpSchemataToXML('Target1', self.container.atse_getSchemataNames('Target1', False))
        self.container._clear()
        self.container.atse_doImportStringXML('Target1', dstr)
        self.failUnless('Target1' in self.container.atse_getRegisteredSchemata())
        dstr2 = self.container.atse_dumpSchemataToXML('Target1', self.container.atse_getSchemataNames('Target1', False))
        self.failUnless(len(dstr)==len(dstr))

    def test_rightsManagement(self):

        fl = self.container.atse_getField('Target1', 'additionalField')

        # test for access with Anonymous
        self.container.atse_setFieldRightsForRole(fl, view='Manager',modify='Manager', delete='Manager', manage='Manager')
        self.container.atse_updateManagedSchema('Target1', None, update_all=True)
        newSecurityManager(None, self.user_anonymous)
        self.failIf(fl.checkPermission('r', fl))
        self.failIf(self.target1.Schema().editableFields(self.target1))
        self.failIf(fl.atse_readable(fl))
        self.failIf(fl.writeable(fl))
        self.failIf(self.container.atse_userCanDelete(fl))
        self.failIf(self.container.atse_userCanManageRights(fl))

        # test with Anonymous allowed to view and delete field
        self.container.atse_setFieldRightsForRole(fl, view='Anonymous',modify='Manager', delete='Anonymous', manage='Manager')
        self.container.atse_updateManagedSchema('Target1', None, update_all=True)
        self.failUnless(fl.checkPermission('r', fl))
        self.failUnless(fl.atse_readable(fl))
        self.failIf(fl.writeable(fl))
        self.failUnless(self.container.atse_userCanDelete(fl))

        # should work for Manager
        newSecurityManager(None, self.user_manager)
        self.failUnless(self.container.atse_userCanDelete(fl))
        self.failUnless(fl.checkPermission('r', fl))
        self.failUnless(fl.checkPermission('w', fl))
        self.failUnless(fl.checkPermission('r', self.target1))
        self.failUnless(fl.checkPermission('w', self.target1))

        # check access for normal Member role
        self.container.atse_setFieldRightsForRole(fl, view='Anonymous',modify='Member', delete='Anonymous', manage='Manager')
        self.container.atse_updateManagedSchema(self.target1.portal_type, 'default', update_all=True)
        newSecurityManager(None, self.user_member)
        self.failUnless(fl.checkPermission('w', self.target1))
        self.failUnless(fl.checkPermission('r', self.target1))
        self.failUnless(fl.writeable(self.target1))

        # we must check a special case where at_isEditable breaks
        # this case also implicitly tests if global update mech works (update_all=True)
        ss = self.target1.Schema()
        self.failUnless(hasattr(ss['additionalField'], 'atse_field_modify_right'))
        ata = ss.editableFields(self.target1)
        self.failUnless(len(ata)>0)

    def test_updateManagedSchemaFunctionality(self):
        ss = self.target1.Schema()['additionalField']
        self.failUnless('view' in list(ss.widget.modes), 'Mode is %s' % list(ss.widget.modes))
        self.container._schemas['Target1']['additionalField'].widget.modes = ('edit',)
        self.failUnless('view' in list(ss.widget.modes))
        #self.container.atse_updateManagedSchema(self.target1.portal_type, 'default', update_all=True)
        #self.failIf('view' in list(ss.widget.modes))

    def test_addField(self):
        original_schema = self.target1.Schema().copy()
        name = 'addedField'
        self.failIf(original_schema.has_key(name))

        self.container.atse_addField(self.target1.portal_type, 'default', '' , name)
        # updating all portal_types
        self.container.atse_updateManagedSchema(self.target1.portal_type, '', update_all=True)
        new_schema = self.target1.Schema()
        self.failUnless(new_schema.has_key(name))
        
    def test_updateObjectSchema(self):
        original_schema = self.target1.Schema().copy()
        name = 'additionalField'
        # deleting - only Manager can do that at the moment
        newSecurityManager(None, self.user_manager)
        self.container.atse_delField(self.target1.portal_type, '' , name)
        # updating all portal_types
        self.container.atse_updateManagedSchema(self.target1.portal_type, '', update_all=True)
        new_schema = self.target1.Schema()
        self.assertNotEqual([x.getName() for x in original_schema.fields()], [x.getName() for x in new_schema.fields()])

    def test_registerWidget(self):
        self.container.atse_registerWidget('NewStringWidget', NewStringWidget(),
                                           visible=True)
        widget_info = self.container.atse_getWidgetInfo()
        right_widget_data = ('NewStringWidget', {'widget':NewStringWidget(),
                                                 'visible':True})
        last_widget_data = widget_info[-1]
        self.assertEqual(last_widget_data[0], right_widget_data[0])
        self.assertEqual(last_widget_data[1]['visible'],
                         right_widget_data[1]['visible'])
        self.assertEqual(last_widget_data[1]['widget'].__class__,
                         right_widget_data[1]['widget'].__class__)
        
        widget_map = self.container.atse_getWidgetMap()
        self.failUnless(widget_map.has_key(right_widget_data[0]))
        self.assertEqual(widget_map, dict(widget_info))

    def test_registerField(self):
        new_field_type_name = 'NewStringField'
        self.container.atse_registerFieldType(new_field_type_name,
                                              NewStringField)
        field_types = self.container.atse_getFieldTypes()
        self.failUnless(new_field_type_name in field_types)

    def test_referenceField(self):
        name = 'refField'
        self.container.atse_addField(self.target1.portal_type, 'default', '', name)

        field_data = {'type': 'ReferenceField',
                      'schemata': 'default', 'name': name,
                      'widget': 'ReferenceBrowserWidget',
                      'label': 'refField', 'storage': 'Attribute',
                      'relationship': 'testRelation'}
        fd = record()
        for key, value in field_data.items():
            setattr(fd, key, value)
        self.container.atse_update(self.target1.portal_type, '', fd,
                                   self.container.REQUEST)
                                   
        self.container.atse_updateManagedSchema(self.target1.portal_type, '', update_all=True)
        self.target1.addReference(self.target2, relationship='testRelation')
        field = self.target1.getField(name)
        self.failUnless(field.getAccessor(self.target1)() == self.target2)
        self.failUnless(field.getEditAccessor(self.target1)() == \
                        self.target2.UID())

    def test_readdFirstField(self):
        field = self.target1.Schema().fields()[0]
        fname = field.getName()
        newSecurityManager(None, self.user_manager)
        self.container.atse_delField(self.target1.portal_type, 'default',
                                     fname)
        self.container.atse_updateManagedSchema(self.target1.portal_type, 'default', update_all=True)
        self.failIf(self.target1.getField(fname))

    def test_strangeCollectionRelatedError(self):
        self.container.atse_registerPortalType('Collection')
        self.collection = makeContent(self.container, 'Collection', id='collection')

    def test_DataGrid(self):
        self.container._clear()
        self.container.atse_registerPortalType('Target4')

        # XXX: implement this

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSchemaEditor))
    return suite

if __name__ == '__main__':
    framework()
