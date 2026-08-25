# Ejemplo Práctico: Agente de Agendamiento (Scheduling Bot)

Este documento aterriza la arquitectura de conocimiento tipado (SLDB) y la máquina de estados en un caso de uso real: un bot de reservas para una clínica o negocio.

## 1. Conexión con Canales Externos (Ej. Twilio)
La arquitectura está diseñada para vivir en **Modal** (serverless) consumiendo la SDK de Gemini. ¿Cómo entra Twilio aquí?
- **El Gateway (FastAPI)** expone un endpoint `POST /webhook/twilio`.
- Cuando Twilio recibe un WhatsApp, hace un POST a ese endpoint.
- El endpoint convierte el formato de Twilio a un mensaje estándar (`ChatRequest`) y lo empuja a la Máquina de Estados (estado `buffering` para evitar spam).
- Cuando el *Conversador* redacta la respuesta final, en lugar de devolver JSON a un navegador, el Gateway usa la SDK de Twilio (`client.messages.create`) para enviar la respuesta de vuelta al número del usuario.
*(Revisar el diagrama "Despliegue · Backend vs Frontend" actualizado en el catálogo para ver esta conexión).*

---

## 2. Taxonomía de la KB (SLDB) para Agendamiento

En lugar de programar con `if/else` en Python, toda la lógica del negocio se define en **Átomos Tipados** dentro de SLDB. El Ontologizador leerá esto en tiempo real.

| Tipo de Átomo | ID en SLDB | Contenido (Conocimiento Abstracto) |
|---|---|---|
| **DomainAtom** | `atom-horarios-atencion` | "Atendemos de Lunes a Viernes de 09:00 a 18:00. Fines de semana cerrado." |
| **DomainAtom** | `atom-catalogo-servicios` | "Servicios: 1. Limpieza dental ($30). 2. Ortodoncia ($100)." |
| **RuleAtom** | `atom-regla-cancelacion` | "Si el usuario cancela con menos de 24h de aviso, aplicar penalidad y requerir pago adelantado la próxima vez." |
| **RuleAtom** | `atom-regla-tono` | "Si el usuario está molesto, pedir disculpas antes de ofrecer reagendar." |
| **ToolAtom** | `atom-tool-google-calendar` | *Esquema JSON*: `check_availability(date)`, `book_appointment(date, service)`. |
| **TraitAtom** (Perfil) | `trait-paciente-frecuente` | "El usuario ha venido más de 5 veces. Ofrecer descuentos." |
| **TraitAtom** (Perfil) | `trait-no-show` | "El usuario faltó a su última cita. Requerir confirmación doble." |

*(El **Perfilador** asigna dinámicamente los TraitAtoms al `user_id` en SQL).*

---

## 3. Flujo en la Máquina de Estados (Paso a Paso)

Imagina que el usuario envía por WhatsApp: *"Hola, necesito limpieza dental para mañana."*

1. **`idle` → `buffering`**
   - Entra el webhook de Twilio. El sistema espera 2 segundos por si el usuario manda un segundo mensaje ("ah, y que sea en la tarde").
2. **`buffering` → `evaluating_context` (Ontologizador)**
   - El Ontologizador compila el contexto evaluando la función matemática `p()`:
     - **Pregunta**: "Limpieza dental mañana en la tarde".
     - **Dominio extraído**: `atom-catalogo-servicios` (tiene limpieza), `atom-horarios-atencion`.
     - **Tools disponibles**: `atom-tool-google-calendar`.
     - **Perfil (SQL -> SLDB)**: Resulta que el usuario tiene el `trait-no-show`.
   - *Contexto generado*: "Usuario quiere limpieza mañana PM. Es usuario con historial de inasistencia (pedir confirmación extra). Debe revisar calendario."
3. **`evaluating_context` → `waiting_tool`**
   - El Conversador recibe el contexto. Ve que debe revisar disponibilidad.
   - Pausa la conversación y emite el comando `check_availability(mañana PM)`.
4. **`waiting_tool` → `evaluating_context`**
   - La API de Google Calendar retorna: `{"slots": ["15:00", "16:30"]}`. Se inyecta al contexto.
5. **`evaluating_context` → `drafting_response` (Conversador)**
   - El Conversador redacta (usando Gemini): 
     *"¡Hola! Tengo disponibilidad mañana a las 15:00 y 16:30 para tu limpieza dental. Como faltaste a tu cita anterior, te pediré que me confirmes con un 'Sí' seguro para bloquear la agenda. ¿Qué hora prefieres?"*
6. **`drafting_response` → `idle`**
   - Se envía vía Twilio. Vuelve a esperar.
