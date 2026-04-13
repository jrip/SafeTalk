FROM node:22-alpine AS dashboard
WORKDIR /src
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm install
COPY dashboard/ ./
RUN npm run build

FROM nginx:alpine

RUN apk add --no-cache openssl \
    && mkdir -p /etc/nginx/ssl \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/self.key \
        -out /etc/nginx/ssl/self.crt \
        -subj "/CN=localhost"

RUN rm -f /etc/nginx/conf.d/default.conf

COPY static/index.htm /usr/share/nginx/html/index.htm
COPY --from=dashboard /src/dist /usr/share/nginx/html/dashboard
COPY web-proxy/nginx.conf /etc/nginx/conf.d/app.conf
