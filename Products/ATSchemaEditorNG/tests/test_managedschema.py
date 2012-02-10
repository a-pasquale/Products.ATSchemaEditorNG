#
#  ATSchemaEditorNG TestCase
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.Archetypes.public import StringField, StringWidget

from Products.ATSchemaEditorNG.examples.content import Target4
from atse_testcase import ATSETestCase, makeContent

class TestManagedSchema(ATSETestCase):

    def afterSetUp(self):
        self.installDependencies()
        self.createBasicSetup()
        self.fs_schema = Target4.schema
        self.container.atse_registerObject(self.target4, ('metadata',))

    def test_explicitDef(self):
        t4 = self.target4
        field = t4.getField('explicit_def')
        accessor = field.getAccessor(t4)
        t4.accessor_called = False
        accessor()
        self.failUnless(t4.accessor_called)

        mutator = field.getMutator(t4)
        t4.mutator_called = False
        mutator('some value')
        self.failUnless(t4.mutator_called)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestManagedSchema))
    return suite

if __name__ == '__main__':
    framework()
