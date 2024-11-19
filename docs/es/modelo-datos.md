Modelo de datos *abstracto* de devicehub que ayuda a tener una idea de cómo funciona

Recordad que por ser este un proyecto de django, se puede obtener de forma automatizada un diagrama de datos con el comando `graph_models` (más adelante vemos de documentar mejor cómo generarlo)

```mermaid
erDiagram

    %% los snapshots/placeholders son ficheros de FS inmutables, se insertan en xapian
    %%   y via su uuid se anotan
    %% placeholders también se pueden firmar (como un spnashot, otra fuente)
    EVIDENCE {
        json obj "its uuid is the PK"
    }

    USER {
        int id PK
        string personal-data-etc
    }

    %% includes the relevant CHID with algorithm for the device build
    EVIDENCE_ANNOTATION {
        int id PK
        uuid uuid "ref evidence (snapshot,placeholder)"
        string key
        string value
        int type "0: sys_deviceid, 1: usr_deviceid, 2: user"
        ts created
        int owner FK
    }

    ALGORITHM {
        string algorithm
    }

    %% todas las anotaciones que tienen CHID
    %% y su key es un algoritmo de los que tenemos

    %% un device es una evaluación

    DEVICE {
        string CHID
    }

    DEVICE_ANNOTATION {
        string CHID FK
        string key
        string value
        uuid uuid "from last snapshot"
    }

    LOT {
        int id PK
        string name
        string code "id alt legacy"
        string description
        bool closed
        int owner FK
        ts created
        ts updated

    }

    LOT_ANNOTATION {
        string id FK
        string key
        string value
    }

    SNAPSHOT ||--|| EVIDENCE: "via workbench"
    PLACEHOLDER  ||--|| EVIDENCE: "via webform"

    EVIDENCE ||--|{ EVIDENCE_ANNOTATION: "are interpreted"
    USER ||--|{ EVIDENCE_ANNOTATION: "manually entered"
    ALGORITHM ||--|{ EVIDENCE_ANNOTATION: "automatically entered"
    EVIDENCE_ANNOTATION }|--|{ DEVICE: "aggregates"
    DEVICE }|--|{ LOT: "aggregates"

    DEVICE ||--|| DEVICE_ANNOTATION: "enriches data"
    LOT ||--|| LOT_ANNOTATION: "enriches data"
```
