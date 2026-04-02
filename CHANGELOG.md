# Changelog

All notable changes to this project will be documented in this file.

## 2026-04-02

- Fixed a runtime issue in lockdown command handling by wiring the action parameter correctly.
- Simplified lockdown and lockdown config permission logic to one consistent administrator check for non-superusers.
- Removed duplicate settings permission checks that could block superuser-style bypass behavior.
- Improved self-role removal flows:
- Added manageability pre-check in single role leave.
- Made leave all roles remove only manageable roles and report roles that could not be removed.
