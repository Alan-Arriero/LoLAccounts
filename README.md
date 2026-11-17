# Rift Vault

Aplicación de escritorio local para gestionar cuentas de League of Legends en EUW. Consulta los Riot IDs y rangos con la API oficial de Riot, mantiene el perfil activo local y permite filtrar la colección por elo, nombre, etiqueta o porcentaje de victorias.

## Inicio de escritorio

Instala Poetry y abre launch.vbs para iniciar Rift Vault sin una consola visible. Para usar el lanzador de desarrollo launch.bat o PowerShell:

poetry install
poetry run python main.py

La app se abre en una ventana nativa de Windows con WebView2. Si Windows no encuentra el motor WebView2, instala Microsoft Edge WebView2 Runtime desde el sitio de Microsoft.

## API de Riot

La clave se carga desde .env en el backend y ese archivo está excluido de Git. Para registrar otra clave, reemplaza RIOT_API_KEY en .env. El endpoint de cuentas usa la ruta regional europe; los datos clasificatorios se consultan en euw1.

Las cuentas y sus etiquetas se almacenan en SQLite local (league_accounts.db). Las contraseñas se guardan aparte en el Administrador de credenciales de Windows.


## Inicio de sesión

Al añadir una cuenta puedes guardar el usuario y la contraseña de Riot. La contraseña se conserva en el Administrador de credenciales de Windows; la base de datos no contiene contraseñas. El botón abre Riot Client y permite completar allí el acceso manualmente.

## Descargas

Cada tag v* genera una release de Windows en GitHub Actions. Extrae el ZIP y ejecuta LoLAccounts.exe. La API key no se incluye en el paquete: copia .env.example a .env y añade tu clave de Riot en esa carpeta.

