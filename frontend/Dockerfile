# Frontend image — static SPA served by nginx.
# Build context: frontend/ (see frontend/.dockerignore).

# ---------- build: Node + node_modules + TypeScript, discarded afterwards
FROM node:20-alpine AS build
WORKDIR /src

# Lockfile first so `npm ci` stays cached until dependencies change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---------- serve: nginx only. The unprivileged variant runs as UID 101 on 8080.
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html

EXPOSE 8080
