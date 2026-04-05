import json

def filtrar_diccionario(archivo_entrada, archivo_salida):
    try:
        with open(archivo_entrada, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        diccionario_limpio = []
        
        for var in datos:
            # 1. Obtener la lista de fuentes de forma segura
            sources = var.get("sources", [])
            
            # 2. Verificar si la lista tiene al menos un elemento
            # Si tiene algo, toma el primero. Si no, usa "NASA" por defecto.
            fuente = sources[0] if (isinstance(sources, list) and len(sources) > 0) else "NASA"
            
            item = {
                "id": var.get("id"),
                "nombre": var.get("name"),
                "fuente": fuente,
                "rango": var.get("range", {}),
                "unidades": "Por definir" 
            }
            diccionario_limpio.append(item)
        
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(diccionario_limpio, f, indent=4, ensure_ascii=False)
        
        print(f"¡Éxito! Se filtraron {len(diccionario_limpio)} variables sin errores.")
        
    except FileNotFoundError:
        print(f"Error: No encontré el archivo '{archivo_entrada}'.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

# Ejecutar
filtrar_diccionario('parametros.json', 'diccionario_limpio.json')