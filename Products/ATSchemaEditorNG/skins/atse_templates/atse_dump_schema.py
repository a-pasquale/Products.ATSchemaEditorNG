##parameters=schema_id

# Dump schema
#
# This code stinks less and still works :-)

print "#<pre>"
print "######################################################################"
print "# Schema created by ATSchemaEditorNG                                 #"
print "# (C) 2004, ZOPYX Software Development and Consulting Andreas Jung   #"
print "# Published under the Lesser GNU Public License LGPL V 2.1           #"
print "######################################################################"
print 
print "from Products.Archetypes.public import *"
print 
print 
print "schema = BaseSchema + Schema(("


schema = context.atse_getSchemaById(schema_id)

for schemata_name in context.atse_getSchemataNames(schema_id):
    schemata = context.atse_getSchemata(schema_id, schemata_name)
    schemataString = context.atse_dumpSchemata(schema_id, schemata_name)
    print '%s' % schemataString 

print  "))"
        
print "#</pre>"
return printed
