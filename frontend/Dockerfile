# The MediTrack web image: build the SPA, then serve it with nginx as a non-root user (docs/security.md §4).

FROM node:22.23.4-alpine AS build
WORKDIR /app
# Dependencies first, so they're cached until the lock file changes.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# nginx-unprivileged runs as a non-root user and listens on 8080; its pid and temp files live in /tmp.
FROM nginx/nginx-unprivileged:1.30.6-alpine3.24
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
