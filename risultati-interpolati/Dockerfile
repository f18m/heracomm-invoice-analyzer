# Usa l'immagine ufficiale di Nginx come base
FROM nginx:alpine

# Informazioni sul maintainer
LABEL maintainer="Energy Analytics Team"
LABEL description="Web server per l'analisi dei consumi energetici"
LABEL version="1.0"

# Crea la directory per l'applicazione
WORKDIR /usr/share/nginx/html

# Rimuovi il contenuto default di nginx
RUN rm -rf /usr/share/nginx/html/*

# Copia il file HTML dell'applicazione
COPY energy_consumption_interpolation.html /usr/share/nginx/html/index.html

# Copia la configurazione personalizzata di Nginx (opzionale)
COPY nginx.conf /etc/nginx/nginx.conf

# Crea directory per i log
RUN mkdir -p /var/log/nginx

# Imposta i permessi corretti
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Esponi la porta 80
EXPOSE 80

# Aggiungi health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Installa curl per l'health check
RUN apk add --no-cache curl

# Comando per avviare nginx
CMD ["nginx", "-g", "daemon off;"]