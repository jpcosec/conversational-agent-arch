---
# routine-xxx
id: routine-task-conectar-el-runtime-a-twilio-whatsapp-sms
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-execution-ready
- operator-task-conectar-el-runtime-a-twilio-whatsapp-sms-activate
- checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-testing-ready
- operator-task-conectar-el-runtime-a-twilio-whatsapp-sms-ready-for-testing
- checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-closeout-ready
- operator-task-conectar-el-runtime-a-twilio-whatsapp-sms-close
# Edge identifiers composing the graph
edges:
- edge-task-conectar-el-runtime-a-twilio-whatsapp-sms-execution-to-activate
- edge-task-conectar-el-runtime-a-twilio-whatsapp-sms-activate-to-testing
- edge-task-conectar-el-runtime-a-twilio-whatsapp-sms-testing-to-ready
- edge-task-conectar-el-runtime-a-twilio-whatsapp-sms-ready-to-closeout
- edge-task-conectar-el-runtime-a-twilio-whatsapp-sms-closeout-to-close
- edge-task-conectar-el-runtime-a-twilio-whatsapp-sms-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Conectar el runtime a Twilio (WhatsApp/SMS)

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Conectar el runtime a Twilio (WhatsApp/SMS).
