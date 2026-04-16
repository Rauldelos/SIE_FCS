FROM php:8.2-apache-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    unzip \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libzip-dev \
    libicu-dev \
    libxml2-dev \
    libc-client-dev \
    libkrb5-dev \
    libldap2-dev \
    libcurl4-openssl-dev \
    libonig-dev \
    && rm -rf /var/lib/apt/lists/*

RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-configure imap --with-kerberos --with-imap-ssl \
    && docker-php-ext-configure ldap --with-libdir=lib/x86_64-linux-gnu/ \
    && docker-php-ext-install -j$(nproc) \
    gd zip mysqli pdo_mysql intl xml opcache imap soap ldap curl mbstring

RUN a2enmod rewrite

# Alternativa1: Copiamos el contenido de la carpeta con los ficheros de SuiteCRM al contenedor
# Problema: La carpeta tiene muchos ficheros y el proceso es lento
# COPY ./SuiteCRM-8.9.1 /var/www/html

# Alternativa2: Copiamos el ZIP al contenedor, lo descomprimimos y eliminamos el ZIP
# Problema: El ZIP es demasiado grande para subirlo al repositorio de GitHub (límite=100MB)
# COPY ./SuiteCRM-8.9.1.zip /tmp/SuiteCRM.zip
# RUN unzip /tmp/SuiteCRM.zip -d /var/www/html \
#     && rm /tmp/SuiteCRM.zip

# Alternativa3: Descargamos el ZIP desde la web oficial, lo descomprimimos y eliminamos el ZIP
WORKDIR /var/www/html
RUN curl -L https://github.com/salesagility/SuiteCRM-Core/releases/download/v8.9.1/SuiteCRM-8.9.1.zip -o suitecrm.zip \
    && unzip suitecrm.zip \
    && rm suitecrm.zip \
    # Mover archivos si se descomprimen en una subcarpeta
    && if [ -d "SuiteCRM-8.9.1" ]; then cp -r SuiteCRM-8.9.1/. .; rm -rf SuiteCRM-8.9.1; fi

# Ajustar permisos estrictos y crear carpetas necesarias para evitar errores
RUN mkdir -p /var/www/html/cache \
    /var/www/html/public/legacy/cache \
    /var/www/html/public/legacy/custom \
    /var/www/html/public/legacy/modules \
    /var/www/html/public/legacy/themes \
    /var/www/html/public/legacy/data \
    && chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html \
    && chmod -R 777 /var/www/html/cache \
    && chmod -R 777 /var/www/html/public/legacy/cache \
    && chmod -R 777 /var/www/html/public/legacy/custom \
    && chmod -R 777 /var/www/html/public/legacy/modules \
    && chmod -R 777 /var/www/html/public/legacy/themes \
    && chmod -R 777 /var/www/html/public/legacy/data

# Configuración personalizada de PHP para SuiteCRM
RUN echo "memory_limit=512M" > /usr/local/etc/php/conf.d/suitecrm.ini \
    && echo "upload_max_filesize=20M" >> /usr/local/etc/php/conf.d/suitecrm.ini \
    && echo "post_max_size=20M" >> /usr/local/etc/php/conf.d/suitecrm.ini \
    && echo "max_execution_time=300" >> /usr/local/etc/php/conf.d/suitecrm.ini \
    && echo "display_errors=Off" >> /usr/local/etc/php/conf.d/suitecrm.ini \
    && echo "error_reporting=E_ALL & ~E_DEPRECATED & ~E_STRICT & ~E_NOTICE & ~E_WARNING" >> /usr/local/etc/php/conf.d/suitecrm.ini

WORKDIR /var/www/html
EXPOSE 80