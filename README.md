# Infraestructura SIE

Este repositorio contiene la configuración necesaria para levantar el ecosistema de la asignatura **Sistemas de Información Empresariales** (SIE). Configuraremos un entorno profesional utilizando GitHub y Docker, lo que nos permitirá realizar las actividades planificadas con diferentes herramientas de gestión empresarial, usando todos la misma infraestructura, minimizando los problemas técnicos y facilitando la limpieza del equipo una vez finalizado el trabajo.

## 📑 Índice
- [Infraestructura SIE](#infraestructura-sie)
  - [📑 Índice](#-índice)
  - [🧰 Herramientas](#-herramientas)
  - [📂 Estructura del Repositorio](#-estructura-del-repositorio)
  - [🛠️ Requisitos y Herramientas Externas](#️-requisitos-y-herramientas-externas)
  - [🚀 Inicio Rápido](#-inicio-rápido)
  - [⚙️ Configuración](#️-configuración)
    - [A. SuiteCRM (CRM)](#a-suitecrm-crm)
    - [B. smtp4dev (Servidor de correo electrónico)](#b-smtp4dev-servidor-de-correo-electrónico)
    - [C. Bonita Runtime (BPM)](#c-bonita-runtime-bpm)
    - [D. Odoo (ERP)](#d-odoo-erp)
      - [Módulos Personalizados en Odoo (Addons)](#módulos-personalizados-en-odoo-addons)
    - [E. n8n (iPaaS)](#e-n8n-ipaas)
    - [F. pgAdmin (Gestión de Bases de Datos PostgreSQL)](#f-pgadmin-gestión-de-bases-de-datos-postgresql)
    - [G. phpMyAdmin (Gestión de Bases de Datos MariaDB/MySQL)](#g-phpmyadmin-gestión-de-bases-de-datos-mariadbmysql)
  - [🖥️ Alternativas (Instalación Local)](#️-alternativas-instalación-local)
  - [❓ FAQ y Resolución de Problemas](#-faq-y-resolución-de-problemas)

<span id="herramientas"></span>
## 🧰 Herramientas
Las herramientas con las que vamos a trabajar son:

| Herramienta | Categoría | Función Principal |
|------------|-----------|-------------------|
| Docker | Virtualización y Contenedores | Plataforma que permite ejecutar y aislar las aplicaciones para que funcionen igual en cualquier PC. |
| Odoo | ERP (Enterprise Resource Planning) | Gestión integral: ventas, inventario, contabilidad y RRHH. |
| SuiteCRM | CRM (Customer Relationship Management) | Gestión del ciclo de vida del cliente y marketing. |
| Bonita | BPM (Business Process Management) | Automatización y ejecución de procesos de negocio complejos. |
| n8n | iPaaS (Integration Platform as a Service) | Conecta diferentes aplicaciones mediante flujos de trabajo automatizados. |
| smtp4dev | Servidor de Email de Pruebas | Atrapa los correos salientes de las apps para verlos en un panel local sin enviar emails reales. |
| pgAdmin | Administración de Bases de Datos PostgreSQL | Interfaz web para administrar y monitorizar bases de datos PostgreSQL. |
| phpMyAdmin | Administración de Bases de Datos MariaDB/MySQL | Interfaz web para administrar y monitorizar bases de datos MariaDB o MySQL. |


<span id="estructura"></span>
## 📂 Estructura del Repositorio

* `odoo/`:
    * `addons/`: Carpeta para tus módulos personalizados.
    * `config/`: Contiene el fichero `odoo.conf` de configuración.
* `suitecrm/`:
    * `languages/`: Contiene el pack de idioma español (.zip) listo para instalar tras lanzar el servicio. Puedes descargar y añadir aquí otros idiomas si lo deseas (más abajo se describe cómo hacerlo).
    * `upload/`: Carpeta local para persistir archivos subidos al CRM.
    * `Dockerfile`: Instrucciones de construcción de la imagen de PHP personalizada.
* `bonita/`: 
    * `exports/`: Directorio recomendado para guardar tus ficheros de Bonita Studio (`.bos`, `.bar`,...).
* `n8n/`:
    * `workflows/`: Carpeta donde exportar tus flujos exportados manualmente (`.json`) desde n8n.
* `docker-compose.yml`: Archivo principal para orquestar todos los servicios.


<span id="requisitos"></span>
## 🛠️ Requisitos y Herramientas Externas

Antes de comenzar, necesitaremos tener instaladas las siguientes herramientas "externas" (que no se encuentran en el repositorio que hemos creado):

1.  **Docker Desktop:** [Descargar](https://www.docker.com/products/docker-desktop/)
    * Es el motor que permite ejecutar todos los servicios (Odoo, SuiteCRM, etc.) contenidos en este repositorio.
    * **IMPORTANTE**: Hay que aceptar la licencia (Docker Subscription Service Agreement) aunque podemos saltarnos los pasos que pidan crear una cuenta o iniciar sesión.
2.  **Acceso a una cuenta de GitHub [OPCIONAL]:** [Enlace](https://github.com)
    * Necesaria para crear y alojar tu propio repositorio a partir del repositorio "plantilla" que proporcionamos.
3.  **Git [OPCIONAL]:** [Descargar](https://git-scm.com/downloads) 
    * Permite mantener tu repositorio actualizado y gestionar versiones. Si no deseas usarlo, puedes descargar el repositorio como un archivo ZIP.
4.  **Bonita Studio 2023.2:** [Descargar](https://www.bonitasoft.com/es/old-versions) 
    * Necesario para diseñar y modelar tus procesos de negocio, que posteriormente se ejecutarán en el motor (Bonita Runtime) incluido en el `docker-compose.yml`. 
    * **IMPORTANTE**: Las versiones de Bonita Studio y de Bonita Runtime deben ser la misma para que los procesos se puedan desplegar correctamente. 
    * Requiere **Java 17** o superior. Puedes descargarlo desde la web de [Adoptium](https://adoptium.net), una opción que usan muchas empresas por tener una licencia más permisiva, o desde [Oracle](https://www.oracle.com/es/java/technologies/downloads), que tiene más restricciones pero que también podemos usar sin coste.


<span id="inicio"></span>
## 🚀 Inicio Rápido

1.  **Crear tu propio repositorio:** Inicia sesión en GitHub y pulsa el botón verde **"Use this template"** arriba a la derecha en el repositorio del curso.
2.  **Nombre del repositorio:** Es OBLIGATORIO que siga el formato: `sie-UVUS` (siendo `UVUS` tu propio UVUS).
3.  **Privacidad:** Privado (si fuera necesario el profesor podrá pedirte que lo añadas como colaborador).
4.  **Clonar o Descargar:** Clona el repositorio, por ejemplo usando `git clone <tu-nueva-url>` o Visual Studio Code, o descarga el ZIP (pulsando el botón `Code` y luego `Download ZIP`) y descomprímelo.
5.  **Arrancar:** Entra en la carpeta desde una terminal y ejecuta: `docker compose up -d --build`.
6.  **Verificar:** Una vez que Docker Desktop indique que los contenedores están en verde, comprueba que puedes acceder a:
    * **Odoo:** [http://localhost:8069](http://localhost:8069)
    * **SuiteCRM:** [http://localhost:8080/public](http://localhost:8080/public)
    * **Bonita Runtime:** [http://localhost:8081](http://localhost:8081)
    * **n8n:** [http://localhost:5678](http://localhost:5678)
    * **smtp4dev:** [http://localhost:3000](http://localhost:3000)
    * **pgAdmin:** [http://localhost:5050](http://localhost:5050)
    * **phpMyAdmin:** [http://localhost:8088](http://localhost:8088)

> **Nota sobre los parámetros de `docker compose up -d --build`:**
>    * El parámetro `-d`activa el "*detached mode*", es decir, ejecuta los contenedores en segundo plano.
>    * El parámetro `--build` solo es necesario la primera vez o si se modifica algún `Dockerfile` usado para crear alguna de las imágenes usadas en el *compose* (no te preocupes por tus datos; gracias a los volúmenes de Docker, no perderás configuraciones ni archivos aunque detengas los contenedores o reconstruyas la imagen).


<span id="configuracion"></span>
## ⚙️ Configuración

En esta sección vamos a comentar aspectos básicos para poder empezar a trabajar con las herramientas incluidas en este repositorio.

<span id="config-suitecrm"></span>
### A. SuiteCRM (CRM)

A diferencia del resto de herramientas, SuiteCRM debe terminar de instalarse una vez lanzado el servicio.

Antes de nada, debemos saber que al acceder al instalador en [http://localhost:8080/public](http://localhost:8080/public) se hace una comprobación inicial que no debe dar errores, pero sí es normal que salgan avisos en el apartado **"ROUTE ACCESS CHECK"** debidos a la naturaleza de la red interna que se usa en Docker. Podemos pulsar **"IGNORE WARNINGS AND PROCEED"** sin problema para continuar con la instalación.

A continuación seguiremos los pasos del asistente de instalación, que nos pedirá que rellenemos lo siguiente:

* **URL OF SUITECRM INSTANCE:** `http://localhost:8080/public`
* **SuiteCRM Database User:** suitecrm_user
* **SuiteCRM Database User Password:** suitecrm_pass
* **Host Name:** db_suitecrm (Es muy importante usar el nombre del servicio de Docker, no "localhost")
* **Database Name:** suitecrm_db
* **Database Port:** 3306 (Es el puerto por defecto de MariaDB)
* **POPULATE DATABASE WITH DEMO DATA?:** Sí (Recomendable para ver ejemplos de cuentas, contactos, etc.).
* **SuiteCRM Application Admin Name:** [escribe el username que quieras para tu usuario administrador, por ejemplo tu *UVUS*]
* **SuiteCRM Admin User Password:** [escribe la contraseña que quieras para tu usuario administrador]
* **Ignore System Check Warnings:** Check

Para poner SuiteCRM en español una vez completado el asistente, accede con el usuario administrador que has creado y sigue estos pasos:
1. **Instalación:** Ve a **Admin** > **Module Loader**, sube el archivo `.zip` que está en la carpeta `suitecrm/languages/`, pulsa **Install** y luego **Commit**.
2. **Verificación:** Ve a **Admin** > **Languages**. Comprueba que el idioma "Spanish" aparece en la columna **Enabled**. Si no es así, muévelo y guarda.
3. **Selección:** Cierra sesión. En la pantalla de Login, verás un selector para elegir "Español".

> **Descarga de traducciones:** Puedes encontrar los paquetes de idioma listos para descargar en [SuiteCRM Translations (SourceForge)](https://sourceforge.net/projects/suitecrmtranslations/files/). Para las versiones más recientes o para colaborar en la traducción, visita [SuiteCRM Crowdin](https://crowdin.com/project/suitecrmtranslations).

---

<span id="config-smtp4dev"></span>
### B. smtp4dev (Servidor de correo electrónico)
Entre las herramientas se encuentra un servidor de correo "fake2 (smtp4dev), que simula el envío de correos electrónicos para hacer pruebas sin necesidad de enviarlos realmente. Será util para configurar las demás herramientas y probar funcionalidades como la creación de nuevos usuarios en SuiteCRM de manera que reciban su contraseña de acceso por email.
También podemos usarlo para que nuestros procesos de negocio en Bonita Studio y Bonita Runtime incluyan una tarea que envíe un email, pero debemos tener en cuenta que la configuración será distinta en ambas herramientas al estar ejecutándose fuera y dentro de Docker respectivamente. A continuación mostramos los parámetros a usar en cada caso.
| Configuración | Desde Docker (Odoo/SuiteCRM/n8n/Bonita Runtime) | Desde fuera de Docker (Bonita Studio) |
| :--- | :--- | :--- |
| **Servidor (Host)** | `smtp4dev` | `localhost` |
| **Puerto SMTP** | `25` | `2525` |

> **Ver Emails:** Accede a [http://localhost:3000](http://localhost:3000) para ver los correos capturados.

---

<span id="config-bonita"></span>
### C. Bonita Runtime (BPM)
Tras lanzar el servicio el sistema no tendrá Organización, BDM ni procesos, que deberán ser desplegados por el usuario denominado "superadministrador", que es el único que inicialmente puede iniciar sesión con las credenciales `install / install`.

---

<span id="config-odoo"></span>
### D. Odoo (ERP)
Al acceder a Odoo por primera vez podremos crear una primera base de datos para gestionar nuestra organización (podemos crear varias, por ejemplo para realizar pruebas). En este punto tendremos que usar la **"Master password"** definida en el fichero `odoo/config/odoo.conf` que por defecto es `admin_password`. También será necesaria para crear nuevas bases de datos o realizar operaciones sobre las bases de datos que ya tengamos creadas. 

#### Módulos Personalizados en Odoo (Addons)
Si has añadido una carpeta de módulo en `odoo/addons/`, sigue estos pasos para que aparezca:
1. **Activar Modo Desarrollador:** Ve a **Ajustes** y, al final de la página, pulsa en **Activar modo desarrollador**.
2. **Actualizar Lista de Aplicaciones:** Ve al menú **Aplicaciones** y, en la barra superior, pulsa en **Actualizar lista de aplicaciones** > **Actualizar**.
3. **Instalar:** Busca tu módulo en el buscador (quita el filtro "Aplicaciones" si no aparece) y pulsa **Instalar**.
> **Nota:** Si has hecho cambios en el código Python del módulo, debes reiniciar el contenedor con `docker compose restart odoo`. Si solo has cambiado XML/CSS, basta con **Actualizar** el módulo desde la interfaz.

---

<span id="config-n8n"></span>
### E. n8n (iPaaS)
Esta herramienta nos permite crear flujos de trabajo que integren diferentes servicios de los que tengamos lanzados en esta infraestructura empresarial. Requerirá crear una cuenta local la primera vez que accedamos.

---

<span id="config-pgadmin"></span>
### F. pgAdmin (Gestión de Bases de Datos PostgreSQL)
Usaremos esta herramienta para poder acceder directamente a las bases de datos PostgreSQL que usan Odoo y Bonita Runtime usando los siguientes datos:
* **Email:** `admin@sie.com`
* **Password:** `admin`

Para añadir los servidores, haz clic derecho en **Servers** > **Register** > **Server...** y usa la siguiente configuración:

**1. Servidor Odoo:**
* **General (Name):** `Odoo DB`
* **Connection (Host name/address):** `db_odoo`
* **Username:** `odoo`
* **Password:** `odoo_pass`

**2. Servidor Bonita:**
* **General (Name):** `Bonita DB`
* **Connection (Host name/address):** `db_bonita`
* **Username:** `bonita`
* **Password:** `bpm`

---

<span id="config-phpmyadmin"></span>
### G. phpMyAdmin (Gestión de Bases de Datos MariaDB/MySQL)
Usaremos esta herramienta para poder acceder directamente a la base de datos MariaDB que usa SuiteCRM usando los siguientes datos:
* **Servidor:** (Ya configurado por defecto como `db_suitecrm`)
* **Usuario:** `suitecrm_user`
* **Contraseña:** `suitecrm_pass` 
>   *(También puedes usar usuario `root` y contraseña `root_pass`)*


<span id="alternativas"></span>
## 🖥️ Alternativas (Instalación Local)
Si por limitaciones de hardware o problemas de otra índole tu equipo no permite ejecutar Docker, hay otras opciones para instalar y ejecutar estas mismas herramientas por separado:

* Odoo: Visita la web oficial y descarga el instalador nativo o usa la versión cloud con restricciones en [https://www.odoo.com/es/page/download](https://www.odoo.com/es/page/download).
* SuiteCRM: Descarga los archivos desde la web oficial de SuiteCRM [https://suitecrm.com/download](https://suitecrm.com/download). Requiere un servidor con PHP y MySQL, recomendamos [XAMPP](https://www.apachefriends.org/es/download.html), y ajustar la configuración de PHP siguiendo las [recomendaciones](https://docs.suitecrm.com/8.x/admin/installation-guide/downloading-installing/). 
* n8n: Usa la versión community de la herramienta siguiendo las indicaciones de la documentación oficial [https://docs.n8n.io/choose-n8n](https://docs.n8n.io/choose-n8n).
* Bonita Runtime: Puedes descargarla desde la misma URL desde la que se descarga Bonita Studio ([https://www.bonitasoft.com/es/old-versions](https://www.bonitasoft.com/es/old-versions)), y recuerda que ambas deben ser de la misma versión. Si no pudiese llevarse a cabo la instalación de Bonita Runtime, Bonita Studio incluye un servidor local para pruebas rápidas que te permitirá validar los procesos que se diseñen.
* smtp4dev: En el repositorio oficial en GitHub podemos encontrar ficheros de instalación para diferentes sistemas operativos [https://github.com/rnwood/smtp4dev/releases](https://github.com/rnwood/smtp4dev/releases).
* pgAdmin: Podemos descargarla desde [https://www.pgadmin.org](https://www.pgadmin.org)
* phpMyAdmin: Incluida en [XAMPP](https://www.apachefriends.org/es/download.html). También podemos descargarla desde [https://www.phpmyadmin.net/downloads/](https://www.phpmyadmin.net/downloads/).


<span id="faq"></span>
## ❓ FAQ y Resolución de Problemas
* **¿Debo aceptar la licencia que me aparece al instalar Docker Desktop?** 
    * Sí, durante el proceso de instalación aparecerá un mensaje sobre los términos de servicio (Docker Subscription Service Agreement) y debéis aceptarlo para poder continuar aunque no es necesario crear una cuenta o iniciar sesión para usar la herramienta. Docker Desktop es gratuito para uso educativo y no es necesario realizar ningún pago ni introducir datos bancarios.
* **¿Qué versión de Docker Desktop debo descargar?**
    * Windows: La mayoría de los ordenadores utilizan la opción AMD64 (procesadores Intel o AMD estándar). Solo elige ARM64 si tienes un dispositivo con procesador basado en arquitectura ARM (como nuevos modelos con chips Snapdragon o series SQ). 
        * Durante la instalación, asegúrate de activar WSL 2. Si la instalación de WSL falla, abre PowerShell como administrador, ejecuta `wsl --install` y reinicia el sistema.
    * macOS: Apple Silicon (ARM64) para modelos con chips M1, M2, M3 o posteriores. Intel Chip (AMD64) para modelos de Mac anteriores a 2020.
    * Linux: Sigue las instrucciones de la web oficial según tu distribución.
* **¿Qué hago si me da un error tipo "port is already allocated"?** 
    * Significa que otra aplicación de tu equipo ya está usando ese puerto. Solución: Abre `docker-compose.yml`, busca el servicio afectado y cambia el primer número del puerto (ej. de 8080:80 a 8082:80). Guarda y ejecuta de nuevo `docker compose up -d --build`.
* **¿Qué hago si obtengo un error "Forbidden" al intentar acceder a SuiteCRM?** 
    * SuiteCRM 8 requiere acceder a través de la carpeta pública. Asegúrate de usar la URL completa: [http://localhost:8080/public](http://localhost:8080/public).
* **¿Se borra mi trabajo si cierro Docker Desktop o apago el equipo?** 
    * No. Los datos persisten en los volúmenes definidos en el `docker-compose.yml`, tanto los internos de Docker como los ligados a las carpetas locales de tu proyecto.
* **¿Cómo detengo los servicios?** 
    * Ejecuta `docker compose stop` en la carpeta del proyecto (aunque no es estrictamente necesario para apagar tu equipo). 
    * También puedes ejecutar `docker compose down` pero ten cuidado y no lo uses con el parámetro `-v` (o `--volumes`) o se borrarán todos los datos guardados hasta la fecha.
* **¿Problemas con la virtualización?** 
    * Si Docker no arranca, verifica en la BIOS que la "Virtualización" (VT-x o AMD-V) esté habilitada.
    * Docker Desktop recomienda un mínimo de 4GB de RAM.
* **¿Cómo empiezo de cero con un servicio instalado eliminando todos los datos creados hasta la fecha?**
    1. Páralo todo con `docker compose down` desde la carpeta del proyecto.
    2. Saca el listado de volúmenes con `docker volume ls`.
    3. Elimina los relacionados con ese servicio con `docker volume rm <VOLUMEN_A_ELIMINAR>`.
    4. Vuelve a lanzar los servicios con `docker compose up -d`.
* **¿Puedo eliminar un servicio por completo?**
    * Sí, por ejemplo, porque hayamos modificado la configuración y necesitemos construirlo desde cero. 
    * Puedes hacerlo con `docker rm -f [SERVICIO]` (Vuelve a lanzarlo con `docker compose up -d --build`).
    * Si lo que quieres es empezar de cero con todo lo que hay en el *compose* ejecuta `docker compose down -v --rmi all --remove-orphans` y termina con `docker system prune -a --volumes`.
* **¿Puedo ver los logs generados en los servicios?** 
    * Sí, con `docker compose logs <SERVICIO>`.
* **¿Por qué tenemos dos servicios de PostgreSQL?** 
    * En esta infraestructura tenemos uno para Odoo y otro para Bonita Runtime. De esta forma, si tuviéramos que eliminar uno o diera cualquier problema no perderíamos los datos del otro.
* **¿Cómo accedo a un fichero que está dentro de un contenedor?**
    * Ejecuta por ejemplo `cat` para ver el contenido con `docker exec -it <CONTENEDOR> cat /ruta/al/archivo.txt`
    * Copia el fichero a tu sistema `Host` con `docker cp <CONTENEDOR>:/ruta/en/contenedor/archivo.txt /ruta/en/host/archivo.txt` 
* **¿Puedo abrir un terminal dentro de un contenedor?**
    * Sí, por ejemplo para instalar modulos adicionales en el intérprete de Python de Odoo (por ejemplo, porque al activar un módulo nos haya salido un error porque falta una dependencia). 
    * Abre un terminal ejecutando `docker exec -it sie_odoo bash`, instala el módulo con `pip` y comprueba si funciona. Por ejemplo, para instalar Pandas ejecutaríamos `pip3 install pandas` y luego `python3 -c "import pandas; print(pandas.__version__)"` para ver si se muestra la versión de Pandas instalada.
    * Para volver al terminal del *Host* ejecuta `exit`, y reiniciamos el servicio si es necesario. Por ejemplo, en el caso de instalar un módulo Python para Odoo será necesario reiniciarlo con `docker restart sie_odoo`.
