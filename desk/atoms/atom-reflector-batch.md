---
id: atom-reflector-batch
title: Reflector Batch
five_wh_one_plus: what
tags:
- layer:runtime
- role:background
- family:domain
provenance: architecture-audit
---

# Reflector Batch

## Answer

Job offline (`ReflectorAtomGenerator`) disparado por cron. Lee el `ChatHistory` ya scrubbeado de SQL, detecta patrones que se repiten >= 5 veces, e infiere nuevos átomos (`domain` o `rule`). Escribe directamente en SLDB usando `sldb docs create` e inyecta el tag de estado `proposed`.
