\# Version Manager Skill



\## Purpose

This skill enforces strict version consistency across the entire NetTools Pro project whenever code is modified.



Versioning is mandatory for every code-changing task.



\---



# NetTools Pro – Version Manager Skill

## Purpose
This skill enforces strict and consistent version management across the entire NetTools Pro project.

Versioning is mandatory for every code modification.



\- If the change is a \*\*small bugfix\*\*, bump \*\*PATCH\*\*

&#x20; - Example: `1.1.0 → 1.1.1`



\- If the change is a \*\*larger bugfix\*\*, \*\*multiple fixes\*\*, or a \*\*feature-level improvement\*\*, bump \*\*MINOR\*\*

&#x20; - Example: `1.1.0 → 1.2.0`



\- If the change introduces \*\*breaking changes\*\*, incompatible behavior, or major architecture changes, bump \*\*MAJOR\*\*

&#x20; - Example: `1.1.0 → 2.0.0`



Never leave the version unchanged after code modifications.



\---



\## REQUIRED VERSION UPDATE LOCATIONS



You MUST update all relevant version references, including:



\- `\_\_version\_\_`

\- `APP\_VERSION`

\- `version\_info.txt`

\- any visible UI version text

\- About dialog / Help / Info panels

\- window title / footer version labels if present

\- README version text if it explicitly shows a release number

\- any build or packaging metadata that embeds the version



If a file contains version text that should not be user-visible but is used during packaging, it must still be updated.



\---



\## VERSION CONSISTENCY RULE



After updating the version:

\- all version references in the project must match

\- no conflicting older version strings may remain in relevant files

\- no partial version bump is allowed



The project version must be treated as a single source of truth reflected consistently everywhere relevant.



\---



\## CHANGE CLASSIFICATION RULE



When deciding which version number to bump:



\### PATCH

Use PATCH for:

\- single bugfixes

\- small UI fixes

\- typo fixes in code or logic

\- narrow stability fixes

\- packaging-only fixes with no user-facing feature change



\### MINOR

Use MINOR for:

\- multiple bugfixes in one pass

\- meaningful feature additions

\- significant improvements to existing tools

\- major usability upgrades

\- stream handling, discovery, routing, viewer, or GUI improvements affecting behavior



\### MAJOR

Use MAJOR for:

\- breaking API changes

\- incompatible config or file format changes

\- major architecture rewrites

\- removal or replacement of core behavior

\- changes that require users to adjust their workflow



If unsure between PATCH and MINOR:

\- prefer \*\*MINOR\*\* if the user-facing behavior clearly improved in a noticeable way



If unsure between MINOR and MAJOR:

\- prefer \*\*MINOR\*\* unless compatibility is actually broken



\---



\## REQUIRED REPORTING



Whenever this skill is used, you MUST report:



1\. the old version

2\. the new version

3\. why that bump level was chosen

4\. every file where version text was updated

5\. confirmation that no conflicting old version strings remain in relevant files



\---



\## VERIFICATION STEPS



After applying changes:



1\. verify that all intended version references were updated

2\. verify syntax still passes for Python files

3\. verify packaging/version files remain valid

4\. verify no duplicate or conflicting version values remain



\---



\## STRICT RULE



If code was modified, versioning is NOT optional.



Never finish a code-changing task without:

\- bumping the version

\- updating all relevant version references

\- reporting the version change


\---


## OPTIONAL (RECOMMENDED)

If CHANGELOG.md exists:
- Append a new entry at the top

If CHANGELOG.md does NOT exist:
- Create CHANGELOG.md

Format:

## [VERSION] - YYYY-MM-DD
- Short summary of changes (clear and concise)