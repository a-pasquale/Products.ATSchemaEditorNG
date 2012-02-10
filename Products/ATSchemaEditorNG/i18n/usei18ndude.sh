#!/bin/sh
TEMPLATES=`find .. -name '*.*pt'`

i18ndude rebuild-pot --pot atschemaeditorng.pot --create ATSchemaEditorNG --merge manual.pot $TEMPLATES
i18ndude sync --pot atschemaeditorng.pot atschemaeditorng-*.po

