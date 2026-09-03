---
id: atom-por-qué-la-respuesta-a-twilio-sale-por-rest-y-no-en-el-twiml
title: Por qué la respuesta a Twilio sale por REST y no en el TwiML
five_wh_one_plus: why
tags:
- layer:runtime
- role:boundary
- topic:canales
- topic:twilio
provenance: kb_agent/inbound.py
---

# Por qué la respuesta a Twilio sale por REST y no en el TwiML

## Answer

Twilio espera la respuesta del webhook a lo sumo 15 segundos; pasado ese plazo descarta la respuesta y reintenta el POST con el mismo `MessageSid`. Un turno completo del runtime (ruteo con embeddings, compilación de contexto, Conversador con Gemini, gate) tardó entre 24 y 36 segundos medido en local el 2026-09-02 contra Vertex AI, y no baja de 15 de forma confiable. Con el modo `sync` original pasaban dos cosas: el usuario nunca recibía el texto (Twilio ya había cortado cuando llegó el TwiML) y cada reintento creaba un turno nuevo con el mismo mensaje, contaminando historial, traits y conversación. Por eso el modo por defecto con credenciales es `async`: el webhook persiste el mensaje y responde `<Response/>` en decenas de milisegundos, el turno corre en background y la respuesta se envía con `client.messages.create` desde el mismo sender al que escribió la persona. La idempotencia por `MessageSid` cubre el caso en que Twilio reintente igual. Consecuencia operativa: para responder por REST hacen falta `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN` de la cuenta dueña del sender (en Modal, ambos en el secret que declara `deploy.twilio_secret_name`), y el background task vive en el contenedor que recibió el webhook: con `min_containers: 1` no es problema, pero si el runtime escalara a cero habría que mover ese trabajo a una función Modal aparte (`.spawn`) para que no muera con el contenedor.
