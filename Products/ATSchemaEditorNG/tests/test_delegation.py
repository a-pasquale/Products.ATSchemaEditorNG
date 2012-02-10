import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.Archetypes import public as atapi
from Products.ATSchemaEditorNG.config import ATSE_MANAGED_NONE
from Products.ATSchemaEditorNG.examples.content import Target3
from atse_testcase import ATSETestCase, makeContent

class TestSchemaDelegation(ATSETestCase):
    """
    test that the 'atse_managed' field attribute is being honored
    by the schema editor
    """
    def afterSetUp(self):
        self.installDependencies()
        self.createBasicSetup()
        self.container.atse_registerObject(self.target3, ('metadata',))
        self.src_schema = Target3.schema

    def test_atse_field_filtering(self):
        schemata_from_atse = self.container.atse_getSchemata('Target3',
                                                             'atse_manage_test')
        atse_fieldnames = [f.getName() for f in schemata_from_atse.fields()]
        src_schemata = self.target3.Schemata()['atse_manage_test']
        fields = src_schemata.filterFields(atse_managed=ATSE_MANAGED_NONE)
        for field in fields:
            self.failIf(field.getName() in atse_fieldnames)

    def test_atse_schemata_filtering(self):
        atse_schema = self.container._schemas['Target3']
        unmanaged_fields = atse_schema.filterFields(atse_managed=ATSE_MANAGED_NONE)
        for field in unmanaged_fields:
            field.schemata = 'filtered_schemata'
        self.failIf('filtered_schemata' in \
                    self.container.atse_getSchemataNames('Target3'))

    def test_atse_syncUnmanagedFields(self):
        atse_schema = self.container._schemas['Target3']
        Target3.schema['atse_managed_full'].foo = 'bar'
        Target3.schema['atse_managed_none'].foo = 'bar'
        self.failIf(getattr(atse_schema['atse_managed_full'], 'foo', None))
        self.failIf(getattr(atse_schema['atse_managed_none'], 'foo', None))
        self.container.atse_syncUnmanagedAndNewFields('Target3')
        self.failIf(getattr(atse_schema['atse_managed_full'], 'foo', None))
        self.failUnless(getattr(atse_schema['atse_managed_none'], 'foo', None))

    def test_atse_syncUnmanagedNewFields(self):
        atse_schema = self.container._schemas['Target3']
        Target3.schema += atapi.Schema((
            atapi.StringField('new_field',)
            ))
        self.failIf(atse_schema.has_key('new_field'))
        self.container.atse_syncUnmanagedAndNewFields('Target3')
        self.failUnless(atse_schema.has_key('new_field'))
    
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSchemaDelegation))
    return suite

if __name__ == '__main__':
    framework()
