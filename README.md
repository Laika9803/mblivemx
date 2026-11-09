# mblivemx — Metrobús CDMX en Vivo

Página web pública con las unidades del Metrobús en vivo (foto actualizada
cada 30 minutos), sin mapa: listas por línea, buscador de estaciones y
unidades más cercanas con llegada estimada.

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` | La página. No depende de ningún servicio externo: solo lee `data.json`. |
| `data.json` | La foto más reciente: líneas, estaciones, rutas y posiciones de las unidades. |
| `refresh.py` | El refresco: valida el acceso, baja el GTFS-RT fresco y reescribe `data.json`. |
| `requirements.txt` | Dependencias de Python para `refresh.py`. |
| `.github/workflows/refresh.yml` | Acción que corre `refresh.py` cada 30 minutos y publica el cambio. |
| `.gitignore` | Evita subir credenciales o archivos temporales. |

## Dominio

El nombre elegido es **mblivemx**. Al 9 de noviembre de 2026, tanto
**mblivemx.com** como **mblivemx.mx** parecían libres (el registro no los
tiene dados de alta). Confírmalo en el registrador antes de pagar.

Precios de referencia (WebHosting MX, noviembre 2026): `.com` ~$304.50 MXN
al año, `.mx` ~$774.59 MXN al año. Recomendado: `.com`, más barato y
universal; `.mx` si prefieres identidad mexicana.

Dónde comprarlo: cualquier registrador acreditado (Neubox, IONOS, NIC México
o el que ya uses). Después apunta el dominio al hospedaje con un registro
CNAME/ALIAS según te indique el proveedor.

## Publicación recomendada (sin servidor propio)

1. Crea un repositorio en GitHub con estos archivos.
2. En el repositorio, guarda los secretos **Settings → Secrets →
   Actions**: `METROBUS_API_USER` y `METROBUS_API_PASS` (los datos de
   acceso al API de Sinoptico/Metrobús). Nunca van en el código.
3. Conecta el repositorio a **Netlify** o **Vercel** (plan gratis) como
   sitio estático y apunta tu dominio ahí.
4. La acción de GitHub (`refresh.yml`) corre sola cada 30 minutos:
   ejecuta `refresh.py`, actualiza `data.json` y lo sube al repositorio;
   Netlify/Vercel redespliega el sitio con los datos nuevos.
5. La página además vuelve a leer `data.json` cada 60 segundos, así que
   quien la tenga abierta ve la foto nueva sin recargar.

## Probar en tu computadora

```bash
python3 -m pip install -r requirements.txt
METROBUS_API_USER=... METROBUS_API_PASS=... python3 refresh.py
python3 -m http.server 8000
# abre http://localhost:8000
```

## Cómo funciona el refresco

1. `refresh.py` hace POST a `partnerValidation` con usuario y contraseña.
2. El API devuelve enlaces temporales (3 horas) para el GTFS estático y
   el GTFS en tiempo real.
3. Descarga el `.proto` en tiempo real y decodifica las posiciones
   (GTFS-Realtime, estándar de Google).
4. Filtra posiciones válidas en CDMX, asigna cada unidad a su línea y
   reescribe `data.json` con la hora de la foto. Las estaciones y rutas
   ya están en `data.json` y casi no cambian, por eso no se descargan
   cada vez.

## Límites honestos

- El feed oficial solo trae **posiciones** de vehículos: no trae tiempos
  de llegada ni alertas. Las llegadas se estiman por distancia (a
  18 km/h en ciudad) y se etiquetan como estimado.
- Muchas unidades no reportan ruta en el feed; la página las agrupa
  como "Sin línea asignada" y las ubica por su estación más cercana.
- Fuente: Metrobús CDMX, datos abiertos GTFS y GTFS-RT. Proyecto no
  oficial, sin afiliación con Metrobús CDMX.
