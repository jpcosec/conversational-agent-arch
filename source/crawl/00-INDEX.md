# Crawl de vitalisuites.com — 2026-08-31

Material fuente crudo del sitio oficial. Insumo humano para redactar KB-atoms.
NO es leído por el runtime. Fuente: https://www.vitalisuites.com/

## Páginas capturadas
- `01-inicio.txt` — / (hero, pilares, testimonios, expansión)
- `02-concepto.txt` — /concepto (4 categorías de amenidades, suites premium)
- `03-proyectos.txt` — /proyectos (6 proyectos con suites/año/amenidades)
- `04-quienes-somos.txt` — /quienes-somos (historia, misión, valores, equipo, KPIs)
- `05-franquicia.txt` — /franquicia (modelo, proceso, datos de mercado, beneficios)
- `06-contacto.txt` — /contacto (formulario, segmentación de leads, oficinas)

## Datos duros extraídos

### Proyectos (6)
| Proyecto | País | Ciudad/Zona | Estado | Suites | Inicio | Amenidades |
|---|---|---|---|---|---|---|
| Ciudad de México | México | CDMX | Planificación | 1000 | 2032 | Spa, Restaurante, Gimnasio, Centro médico, Jardines |
| Chicureo | Chile | Precordillera de Santiago | Set-up | 560 | 2026 | Spa, Restaurante, Gimnasio, Terrazas, Áreas verdes |
| Mantagua | Chile | Zona de alto standing | Set-up | 560 | 2026 | Spa, Restaurante, Biblioteca, Cine, Salón de eventos |
| Bogotá | Colombia | Capital | Planificación | 1000 | 2031 | Spa, Restaurante, Gimnasio, Centro de convenciones, Golf |
| Urubo | Bolivia | Santa Cruz | Planificación | 240 | 2034 | Spa, Restaurante, Piscina, Áreas verdes, Club social |
| Armenia | Colombia | Eje Cafetero | Planificación | 240 | 2033 | Spa, Restaurante, Gimnasio, Jardines, Mirador |

Totales sitio: 6+ proyectos, 500+ suites planificadas, 3 países con presencia.

### Contacto / oficinas
- Tel US: +1 (305) 764-6745
- Tel Chile: +56 9 7663 7338
- Oficina Chile: Av La Dehesa 440, Piso 3. Lo Barnechea, Santiago, Chile.
- Oficina EE.UU.: 8333 NW 53rd St, Suite 450, Doral, FL 33166, EE.UU.
- Email: contacto@vitalisuites.com
- Instagram: @vitalisuiteslatam

### Segmentación de leads (form /contacto)
- 3 tipos: Quiero una Suite / Quiero ser Broker / Quiero una Franquicia
- Campos: nombre, email, teléfono, comuna, ¿para quién? (mí/familiar/inversión),
  rango de edad (<45, 45-59, 60-69, 70+), persona natural/jurídica, RUT,
  ventas mensuales, sitio web, mensaje.

### Equipo directivo
- Pablo Rivas — CEO (MBA, 25+ años, inmobiliario de lujo)
- Nicolás Canales — COO (10+ años, operaciones/tecnología)
- Roberto Pesce — CFO (finanzas, inversores)

### Franquicia (datos de mercado)
- Mercado senior living global: 1.5B USD proyectado 2030
- Crecimiento anual demanda: 32%+
- Adultos mayores LatAm: 150M+
- ROI promedio anual: 12-16%
- Proceso 4 pasos: Factibilidad → Licencia de Marca → Diseño y Construcción → Comercialización Acompañada

## GAPS — lo que Gian pidió y NO está en el sitio
- **Precios ("desde 2376 UF"):** el sitio NO publica precios. Requiere fuente interna.
- **Tipologías / dimensiones (m²) de suites:** el sitio NO las publica. Requiere fuente interna.
- **Modalidad de visita por proyecto:** no está explícita.

## Notas de corrección (bugs reportados por Gian)
- "Ubicación" debe devolver AMBOS proyectos chilenos (Chicureo Y Mantagua), no solo Mantagua.
- Chicureo debe dar ubicación concreta: "precordillera de Santiago" (el sitio no da comuna exacta; Chicureo es sector de Colina/Santiago).
