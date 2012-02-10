#
# PloneTestCase
#

# $Id: atse_testcase.py 39919 2007-03-29 08:17:22Z spamsch $

from Testing import ZopeTestCase
if ZopeTestCase.hasProduct('Five'):
    ZopeTestCase.installProduct('Five')
### ought to be refactored to use CMFTestCase
from Products.CMFPlone.tests import PloneTestCase
from Products.Archetypes.Extensions.utils import installTypes
from Products.Archetypes.public import listTypes
from Products.ATSchemaEditorNG.config import *

from StringIO import StringIO

ZopeTestCase.installProduct('ATSchemaEditorNG')
ZopeTestCase.installProduct('Archetypes')
ZopeTestCase.installProduct('MimetypesRegistry')
ZopeTestCase.installProduct('generator')
ZopeTestCase.installProduct('validation')
ZopeTestCase.installProduct('PortalTransforms')

def makeContent( container, portal_type, id='document', **kw ):
    try:
        container.invokeFactory( type_name=portal_type, id=id )
    except ValueError:
        raise Exception, 'Please set INSTALL_DEMO_TYPES = True in config.py before starting tests'
    return getattr( container, id )

class ATSETestCase( PloneTestCase.PloneTestCase ):
    '''TestCase for ATSchemaEditorNG testing'''

    dependencies=('Archetypes', 'ATSchemaEditorNG')

    def installProducts(self, products):
        self.portal.portal_quickinstaller.installProducts(products=products, stoponerror=1)

    def installDependencies(self):
        self.installProducts(self.dependencies)

    def createBasicSetup(self):
        """ basic schema editing setup """
        
        self.container = makeContent(self.folder, 'Container', id='container')
        self.target1 = makeContent(self.container, 'Target1', id='target1')
        self.target2 = makeContent(self.container, 'Target2', id='target2')
        self.target3 = makeContent(self.container, 'Target3', id='target3')
        self.target4 = makeContent(self.container, 'Target4', id='target4')
        self.target5 = makeContent(self.container, 'Target5', id='target5')

        self.refobject = makeContent(self.container, 'ObjectWithReferences', id='refobject')

