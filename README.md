# Equipo-9
**Materia:** Componentes de Lógica de Negocio  
**Institución:** FIME — UANL  
**Profesor:** Miguel Ángel Gómez Marroquín  

| Integrante | Matrícula |
| :--- | :--- |
| Ivan Francisco Padrón Macías | 2150830 |
| María Ximena Rodarte Cuevas | 2154111 |
| Ángel Haziel Bernal Garza | 2156444 |

```text
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
