# Rift Vault

Aplicación de escritorio local para gestionar cuentas de League of Legends en EUW. Consulta los Riot IDs y rangos con la API oficial de Riot, mantiene el perfil activo local y permite filtrar la colección por elo, nombre, etiqueta o porcentaje de victorias.

Los emblemas Iron–Challenger proceden del paquete oficial [Ranked Emblems Latest de Riot](https://static.developer.riotgames.com/docs/lol/ranked-emblems-latest.zip). La imagen de Yuumi del icono y la interfaz parte de images.jpg.

## Inicio de escritorio

Instala Poetry y abre launch.vbs para iniciar Rift Vault sin una consola visible. Para usar el lanzador de desarrollo launch.bat o PowerShell:

poetry install
poetry run python main.py

La app se abre en una ventana nativa de Windows con Qt WebEngine incluido en el paquete.

## API de Riot

La clave se carga desde `.env` o, si no existe allí, desde el Administrador de credenciales de Windows. El archivo `.env` está excluido de Git. Las versiones nuevas de la app consultan el almacén de Windows para que las instalaciones de este usuario puedan compartir la clave sin incluirla en el repo o en el ZIP público. El endpoint de cuentas usa la ruta regional europe; los datos clasificatorios se consultan en euw1.

Las cuentas y sus etiquetas se almacenan en SQLite local (league_accounts.db). Las contraseñas se guardan aparte en el Administrador de credenciales de Windows.


## Inicio de sesión

Al añadir una cuenta puedes guardar el usuario y la contraseña de Riot. La contraseña se conserva en el Administrador de credenciales de Windows; la base de datos no contiene contraseñas. El botón de inicio abre Riot Client, completa automáticamente el formulario reconocido de Riot y lanza League of Legends tras confirmar la sesión. Si Riot solicita MFA o CAPTCHA, completa ese paso en el cliente.

## Descargas y actualizaciones

Cada tag v* genera una release pública de Windows en GitHub Actions. Extrae el ZIP y ejecuta LoLAccounts.exe. Al iniciar, la app consulta la release pública más reciente; si encuentra una versión nueva, la descarga con indicador de progreso y ofrece reiniciarse para instalarla. El actualizador conserva .env y league_accounts.db.

Si una versión instalada no llega a abrir la interfaz, descarga e instala manualmente la release actual. Una vez que la aplicación inicia normalmente, las versiones posteriores pueden actualizarse automáticamente.

La API key no se incluye en el paquete: copia .env.example a .env y añade tu clave de Riot en esa carpeta.

