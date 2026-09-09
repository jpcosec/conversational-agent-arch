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
    trait: 'Rasgo inferido o registrado sobre una persona usuaria que ayuda a personalizar decisiones futuras.',
    // Terminos de negocio que reemplazan jerga interna en las vistas
    nl: 'Respuesta libre: el agente redacto la respuesta en lenguaje natural, sin ejecutar una tool.',
    kind: 'Tipo de respuesta del turno: respuesta libre, ejecutar tool o no supe responder.',
    gate: 'Validacion: un revisor automatico chequea el borrador contra los criterios del negocio antes de enviarlo; si lo rechaza, se deriva a una persona.',
    grounding: 'Fuente: documento que sostiene el paso activo del flujo; entra al contexto siempre que ese paso este activo.',
    atoms: 'Documentos de la base de conocimiento que entraron al contexto del turno.',
    documento: 'Unidad de conocimiento de la KB (antes llamada atom): una ficha con titulo, familia, tags y contenido.',
    ctx: 'Contexto: los documentos y senales que el agente tuvo a la vista para responder este turno.',
    score: 'Puntaje de similitud semantica entre el mensaje y el documento (0 a 1). Vacio cuando el documento entro por otra razon.',
    motivo: 'Por que entro este documento al contexto: base del negocio, fuente del paso, rasgo del usuario o similitud con el mensaje.',
    piso: 'Base: documentos que entran a todo turno sin excepcion (identidad, limites, reglas).',
    slot: 'Dato que el flujo necesita capturar (nombre, telefono, preferencia de visita...).',
    step: 'Paso del flujo conversacional en el que esta la conversacion.',
    derivado: 'Turno cuyo borrador fue rechazado por la validacion: se le pidio a la persona que espere al equipo.',
    latencia: 'Tiempo desde que llega el mensaje hasta que sale la respuesta.',
    familia: 'Grupo de documentos de la KB: self (identidad), domain (negocio), conversation (flujo), user (rasgos), gate (criterios).',
    ruteador: 'Agente que elige que documentos entran al contexto del turno.',
    orquestador: 'Agente que decide en que paso del flujo esta la conversacion y si hay que ejecutar una tool.',
    conversador: 'Agente que redacta la respuesta que ve la persona.',
    perfilador: 'Agente que, despues de responder, extrae rasgos de la persona para futuros turnos.',
    tool: 'Accion del backend que el agente puede ejecutar (agendar, registrar, consultar).',
    embeddings: 'Vista que ubica cada documento segun su cercania semantica con los demas.'
  };

  globalScope.__glossary = glossary;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = glossary;
    module.exports.__glossary = glossary;
  }
})(typeof window !== 'undefined' ? window : globalThis);
