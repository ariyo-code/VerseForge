# REFACTOR

Record current behavior and tests. Map dependencies and stable interfaces; keep persistence keys, device property names and player state compatibility unchanged unless migration approved. Execute smallest rename/extraction, static checks and actual UEFN compile if available. Compare behavior acceptance matrix and rollback cleanly on regressions. No silent delete/rewrite.
