(function (globalScope) {
  'use strict';

  var glossary = {
    handout: 'Paso conversacional que entrega contenido preparado al usuario, sin recolectar datos nuevos.',
    interaccion_simple: 'Intercambio breve de ida y vuelta donde el agente responde o pregunta sin activar herramientas.',
    obtencion_datos: 'Nodo orientado a capturar slots o información faltante antes de avanzar en el flujo.',
    llamado_tool: 'Paso que ejecuta una ToolAtom o integración externa y luego continúa según el resultado.',
    grounding_atoms: 'Átomos de conocimiento usados para anclar la respuesta en hechos, reglas o contexto disponible.',
    completion_condition: 'Condición que define cuándo un step o escenario ya puede darse por resuelto.',
    allowed_transitions: 'Lista de destinos válidos desde un nodo dentro de la máquina conversacional.',
    required_slots: 'Campos obligatorios que deben estar completos para completar un step o habilitar una transición.',
    system_turn: 'Representación estructurada del turno interno del sistema: decisión, tool, contexto y trazas.',
    tool_call: 'Intención o resultado en el que el agente decide invocar una herramienta específica.',
    fallback: 'Respuesta de seguridad usada cuando no hay contexto suficiente o la intención no se puede resolver bien.',
    breakpoint_miss: 'Señal de que el flujo no encontró el punto esperado de corte o control dentro de la conversación.',
    context_compilation: 'Proceso que selecciona scenario, atoms y señales relevantes antes de generar la respuesta.',
    scenario: 'Marco operativo elegido para el turno actual; resume qué situación cree el sistema que está ocurriendo.',
    flow_node: 'Nodo actual del grafo conversacional donde quedó posicionada la sesión o step activo.',
    trait: 'Rasgo inferido o registrado sobre una persona usuaria que ayuda a personalizar decisiones futuras.'
  };

  globalScope.__glossary = glossary;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = glossary;
    module.exports.__glossary = glossary;
  }
})(typeof window !== 'undefined' ? window : globalThis);
