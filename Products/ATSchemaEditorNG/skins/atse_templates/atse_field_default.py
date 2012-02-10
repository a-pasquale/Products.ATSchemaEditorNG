##parameters=field

"""
ATSchemaEditorNG

(C) 2003,2004, Andreas Jung, ZOPYX Software Development and Consulting
D-72070 Tübingen, Germany

Contact: andreas@andreas-jung.com

License: see LICENSE.txt

$Id: atse_field_default.py 21198 2006-03-22 23:47:40Z rafrombrc $
"""

dm = field.default_method
if dm:
    return field.default_method
else:
    return field.default
