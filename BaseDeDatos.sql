-- ENTIDADES FUERTES (PADRES) 


--EN vim como me muevo en codigo sql tenia problemas no podia avanzar en modo normal para corregir una palabra en especifico
--en vim como copio y pego dentro de los parentesis de tal manera que quede bien tabulado 
--en vim como me muevo hasta el final de la fila para saltar a la siguiente 
--Tomar en cuenta que esta tabla deberia ir en un formato EVA
--En vim como copiar y pegar fuero dentro del sistema 
--En vim como copiamos y pegamos una llinea dentro del codigo 

--Tomar en cuenta que esta tabla deberia ir en un formato EVA

CREATE TABLE climatologia ( 
    id_clima INTEGER PRIMARY KEY, --dudo que realmente sea un entidad independiendiente yo digo que es una entidad de  1 a 1 es decir son como las entidades DAÑOS Y CAUSAS (Dependientes )
    var_climaticas VARCHAR NOT NULL,
    Resultado FLOAT --Le ponemos nulo o no?? 
    fuente VARCHAR NOT NULL --Este atributo es realmente necesario ??La mayoria de las fuentes vendra de la NASA pero tambien debemos tomar en cuenta la vegatacion que es de googleetrs
    Fecha_de_observacion DATE NOT NULL --Tomar en cuenta tambien en la API de la NASA se pediran  datos historicos es decir del mismo incendio registrado se pediran datos climaticos y de vegetacion con dias de antelacion por que se hara un modelo predictivo por eso cuando se almacenan los datos se decidio un modelo EVA para guardalos y despues se aplicara otro metodo para su analisis 
)

