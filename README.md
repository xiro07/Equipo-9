# Equipo-9
**Materia:** Componentes de Lógica de Negocio  
**Institución:** FIME — UANL  
**Profesor:** Miguel Ángel Gómez Marroquín  

| Integrante | Matrícula |
| :--- | :--- |
| Ivan Francisco Padrón Macías | 2150830 |
| María Ximena Rodarte Cuevas | 2154111 |
| Ángel Haziel Bernal Garza | 2156444 |

# Hotel Costa Azul — Sistema de Gestión Hotelera (PMS)

**Materia:** Componentes de Lógica de Negocio  
**Institución:** FIME — UANL  
**Profesor:** Miguel Ángel Gómez Marroquín

## Integrantes

| Integrante | Matrícula |
|---|---:|
| Iván Francisco Padrón Macías | 2150830 |
| María Ximena Rodarte Cuevas | 2154111 |
| Ángel Haziel Bernal Garza | 2156444 |

## Estructura del proyecto

```text
Equipo-9/
├── .gitignore
├── main.py
├── diagramas/
│   ├── dominio/
│   │   ├── diagrama-dominio-ddd.pdf
│   │   └── diagrama-dominio-ddd.png
│   └── secuencia/
│       ├── diagramas-secuencia.pdf
│       └── diagramas-secuencia.png
├── docs/
│   ├── adr/
│   │   ├── adr.docx
│   │   └── adr.pdf
│   ├── bitacora_ia/
│   │   ├── bitacora_ia.docx
│   │   └── bitacora_ia.pdf
│   ├── informe/
│   │   ├── Informe_Arquitectura_E9.docx
│   │   └── Informe_Arquitectura_E9.pdf
│   └── trazabilidad/
│       ├── trazabilidad.docx
│       └── trazabilidad.pdf
├── src/
│   └── costa_azul/
│       ├── __init__.py
│       ├── composicion.py
│       ├── aplicacion/
│       │   ├── __init__.py
│       │   ├── abstracciones.py
│       │   ├── comandos.py
│       │   ├── dtos.py
│       │   └── servicios.py
│       ├── dominio/
│       │   ├── __init__.py
│       │   ├── comun.py
│       │   ├── entidades.py
│       │   ├── enumeraciones.py
│       │   ├── eventos.py
│       │   ├── repositorios.py
│       │   ├── servicios.py
│       │   └── value_objects.py
│       └── infraestructura/
│           ├── __init__.py
│           ├── persistencia.py
│           └── servicios.py
└── tests/
    ├── __init__.py
    ├── test_aplicacion.py
    ├── prueba_arquitectura.py
    ├── test_dominio.py
    ├── test.docx
    ├── test.pdf
    └── escenarios/
        ├── 1.1
        └── 1.2
```

## Descripción de carpetas y archivos

| Carpeta o archivo | Descripción |
|---|---|
| `diagramas/` | Contiene los diagramas de dominio y de secuencia del sistema. |
| `docs/` | Reúne la documentación y las evidencias del proyecto. |
| `docs/adr/` | Contiene las decisiones de arquitectura. |
| `docs/bitacora_ia/` | Incluye el registro del uso de inteligencia artificial. |
| `docs/informe/` | Contiene el informe de arquitectura. |
| `docs/trazabilidad/` | Documenta la relación entre los requisitos y el desarrollo. |
| `src/costa_azul/` | Contiene el código fuente del sistema. |
| `src/costa_azul/aplicacion/` | Coordina los casos de uso. |
| `src/costa_azul/dominio/` | Contiene las entidades y las reglas del negocio. |
| `src/costa_azul/infraestructura/` | Incluye la persistencia y los servicios técnicos. |
| `tests/` | Reúne las pruebas automatizadas y su documentación. |
| `tests/test.docx` y `tests/test.pdf` | Documentos de las pruebas del proyecto. |
| `tests/escenarios/` | Contiene las capturas de los escenarios de prueba. |
| `main.py` | Archivo principal para ejecutar la demostración del sistema. |
| `.gitignore` | Define los archivos que Git debe ignorar. |
