-- ENTIDADES FUERTES (PADRES) 


--EN vim como me muevo en codigo sql tenia problemas no podia avanzar en modo normal para corregir una palabra en especifico
--en vim como copio y pego dentro de los parentesis de tal manera que quede bien tabulado 
--en vim como me muevo hasta el final de la fila para saltar a la siguiente 
--Tomar en cuenta que esta tabla deberia ir en un formato EVA
--En vim como copiar y pegar fuero dentro del sistema 
--En vim como copiamos y pegamos una llinea dentro del codigo 
--En vim como elimino una linea entera de texto ?
--En vim como elimino una palabra entera
--Tomar en cuenta que esta tabla deberia ir en un formato EVA
--Como selecciono 3 lineas de texto para eliminar por completo 
--Como copio y pego 3 lineas de texto u codigo
--En vim como elimino varios espacios en blanco esto me sucede porque le doy enter y pues evidentemente el corchete baja 
--ES UNA ENTIDAD PADRE(QUE NO DEPENDE DE NADIE )
--En vim como cambio de palabra completa a mayuscula?

--ENTIDADES PADRE  (1)
CREATE TABLE diccionario ( 
    id_variable INTEGER PRIMARY KEY, --(deberia ser autoincremental y aparte deberia ser INT ?)dudo que realmente sea un entidad independiendiente yo digo que es una entidad de  1 a 1 es decir son como las entidades DAÑOS Y CAUSAS (Dependientes )
    fuente VARCHAR NOT NULL
    nombre_completo VARCHAR NOT NULL,
    unidad_de_medida FLOAT--LO DEJO PENDIENTE 
    --Fecha_de_observacion FLOAT --Le ponemos nulo o no?? 
    --fuente VARCHAR NOT NULL --Este atributo es rggealmente necesario ??La mayoria de las fuentes vendra de la NASA pero tambien debemos tomar en cuenta la vegatacion que es de googleetrs
    --Fecha_de_observacion DATE NOT NULL --Tomar en cuenta tambien en la API de la NASA se pediran  datos historicos es decir del mismo incendio registrado se pediran datos climaticos y de vegetacion con dias de antelacion por que se hara un modelo predictivo por eso cuando se almacenan los datos se decidio un modelo EVA para guardalos y despues se aplicara otro metodo para su analisis 
);

CREATE TABLE estado (
    id_clave_ent INTEGER PRIMARY KEY,-- (esta no deberia ser autoincremental por que si viene en csv, creo que no se repite si no se repite si requerimos de mas estados ) DEBERIA SER VARCHAR?
    region VARCHAR
    estado VARCHAR 
);

CREATE TABLE vegetacion (
    id_vegetacion INTEGER PRIMARY KEY,--Deberia ser autoincremental? y que tipo de dato
    regimen_del_fuego VARCHAR NOT NULL,
    tipo_de_vegetacion VARCHAR NOT NULL,
);

CREATE TABLE causa(
    id_causa INTEGER PRIMARYKEY,--DEBERIA SER AUTOINCREMENTAL?

    causa VARCHAR NOT NULL 
    causa_especifica VARCHAR NOT NULL
)

--ENTIDADES DE SEGUNDO NIVEL(MUCHOS(N))
--Esta entidad a la vez hijo (N)
CREATE TABLE climatologia(
    id_registro INTEGER PRIMARY KEY,--(deberia ser autoincremental y de tipo INT ?)
    id_variable VARCHAR NOT NULL, --llave foranea que apunta al padre 2
    id_clave_inc VARCHAR NOT NULL, --llave foranea que apunta al padre 1
    fecha_de_observacion DATE NOT NULL,
    resultado_numerico FLOAT NOT NULL,

    FOREIGN KEY (id_variable) REFERENCES diccionario (id_variable), --Un solo registro en el diccionario sirve para identificar a muchos registros en la tabla climatologia 
    FOREIGN KEY (id_clave_inc) REFERENCES incendios (id_clave_inc) --un incendio ocurrio bajo ciertas condiciones climatologicas
);
--Esta entidad a la vez es padre y hijo (1,N)
CREATE TABLE municipios (
    id_cvegeo INTEGER PRIMARY KEY, -- DERBERIA SER VARCHAR?EL CEVEGEO ES EL DEL CSV (COMBINA NUMERO DEL MUCIPIO Y DEL ESTADO, PERO CREO QUE ERA PORQIE EL MUNICIPIO BUENO SU CLAVE TAMBEIN SE REPETIAN LAS CLAVES DE OTROS ESTADOS ENTONCES SE DICIDIO MEJOR PONER EL CVEGEO())
    id_clave_ent INTEGER NOT NULL, --llave foranea que apunta al padre 2
    nombre_municipio VARCHAR NOT NULL,
    FOREIGN KEY (id_clave_ent) REFERENCES estado (id_clave_ent), --Muchos municipios pertenecen a solo estado 
);

--ENTIDAD DE TERCER NIVEL (PADRE)

CREATE TABLE incendios (
    id_clave_inc INTEGER PRIMARY KEY,
    id_cvegeo INTEGER NOT NULL, --llave foranea que apunta al padre 
    id_causa INTEGER NOT NULL, --llave foranea que apunta al padre 
    id_vegetacion INTEGER NOT NULL, --llave foranea que apunta al padre
    latitdu FLOAT NOT NULL,
    longitud FLOAT NOT NULL,
    fecha_inicio DATE NOT NULL,
    Tipo_de_incendio VARCHAR NOT NULL,
    año INTEGER NOT NULL,

    FOREIGN KEY (id_cvegeo) REFERENCES municipios(id_cvegeo) --En un municpio puede ocurri muchos incendios 
    FOREIGN KEY (id_causa) REFERENCES causa(id_causa) -- Muchos incendios pueden haber sido iniciados por la misma cuasa 
    FOREIGN KEY (id_vegetacion) REFERENCES vegetacion(id_vegetacion) --Un tipo de vegetacion puede ser afectado por muchos incendios 

),
--TABLAS HIJAS(1:1)
CREATE TABLE daños (
    id_clave_inc INTEGER PRIMARY KEY,
    horosca FLOAT NOT NULL,
    arbustivo FLOAT NOT NULL,
    herbaceo FLOAT NOT NULL,
    arbolado_adulto FLOAT NOT NULL,
    renuevo FLOAT NOT NULL,
    tamaño VARCHAR NOT NULL, 
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc)

);
