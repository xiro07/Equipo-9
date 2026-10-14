# Equipo-9
**Materia:** Componentes de Lógica de Negocio  
**Institución:** FIME — UANL  
**Profesor:** Miguel Ángel Gómez Marroquín  

| Integrante | Matrícula |
| :--- | :--- |
| Ivan Francisco Padrón Macías | 2150830 |
| María Ximena Rodarte Cuevas | 2154111 |
| Ángel Haziel Bernal Garza | 2156444 |

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
    ├── test_arquitectura.py
    └── test_dominio.py

Descripción de las carpetas y archivos

diagramas/: contiene los diagramas del dominio basados en DDD y los diagramas de secuencia.

docs/: reúne la documentación del proyecto.

adr/: decisiones relacionadas con la arquitectura.

bitacora_ia/: registro del uso de herramientas de inteligencia artificial.

informe/: informe de arquitectura del sistema.

trazabilidad/: documentación de la relación entre los requisitos y las decisiones del proyecto.

src/costa_azul/: contiene el código fuente del sistema.

aplicacion/: coordina los casos de uso y los servicios de aplicación.

dominio/: contiene las entidades, los objetos de valor, los eventos y las reglas del negocio.

infraestructura/: incluye los componentes técnicos relacionados con la persistencia y otros servicios.

composicion.py: configura y conecta los componentes del sistema.

tests/: contiene las pruebas automatizadas de aplicación, dominio y arquitectura.

main.py: archivo principal para ejecutar la demostración del sistema.

.gitignore: indica qué archivos y carpetas debe ignorar Git.
