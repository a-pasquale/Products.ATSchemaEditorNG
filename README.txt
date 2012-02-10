Abstract
========

ATSchemaEditorNG is a framework to provide flexible
schema editing for AT content-types.                               

Current Maintainer:
===================

    Simon Pamies (spamsch)
    EMail: s.pamies at banality dot  de

Original Author:
================

    Andreas Jung, ZOPYX Ltd. & Co. KG
    D-72070 Tuebingen, Germany

License:
========

    ATSchemaEditorNG is (C) by Andreas Jung, Simon Pamies, Rob Miller, and
    contributors, and published as open-source under the GNU Lesser
    General Public License V 2.1 (see LICENSE.txt).  If this license
    does not meet your requirements, contact the maintainers for
    releasing ATSchemaEditorNG under a suitable license.

Requirements:
=============

    Plone 2.5.x, 3.x

Installation:
=============

    See INSTALL.txt

Documentation:
==============

    NOTICE: Please notice that since 0.4 objects that get created
    no longer automatically sync schema with editor schema. If you have
    changes in your editor and then create a new object this object
    will not get changes unless you call self.updateSchemaFromEditor() in
    manage_afterAdd. Please make sure the call is the first one *before*
    you call things like BaseContent.manage_afterAdd

    Example for initializing content object based on ParentManagedSchema or such:

    def manage_afterAdd(self, item, container):
        self.updateSchemaFromEditor()
        BaseContent.manage_afterAdd(self, item, container)

    Look at the examples directory and make sure you read
    docstrings in ParentManagedSchema.py. Also read the
    howto (doc/HOWTO.txt).

Contributions:
==============

    Thanks to gocept for sponsoring some work in 0.4.5

    Thanks to Aaron VanDerlip for useful
    hints about portal_factory failures in 0.4.1

    Many thanks to coreblox (http://coreblox.com)
    for sponsoring all work on 0.4.0

    Whit Morriss: examples and tests

    Rob Miller (rafrombrc): Maintainership until 0.4 - much work
    for 0.3.x line.

    Simon Pamies: fixes, code cleanup, schema update mechanism
                   revisited (and most of the stuff in V 0.2 and 0.4)

    Sasha Vincic: storage registry implementation

