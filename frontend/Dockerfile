# The MediTrack web image: build the SPA, then serve it with nginx as a non-root user (docs/security.md §4).
# Base images are pinned by digest and at least 14 days old, except security releases (docs/security.md §4).

# Node 22.23.3, pushed 2026-09-23. Build stage only; nothing from it but dist/ reaches the image.
FROM node:22.23.3-alpine3.24@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS build
WORKDIR /app
# Dependencies first, so they're cached until the lock file changes.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# nginx 1.30.6 (14 Oct 2026) doesn't wait the 14 days: it's a security release, and 1.30.5 is open to
# CVE-2026-15176, CVE-2026-93479, CVE-2026-95101, CVE-2026-97629 and CVE-2026-97205 (nginx.org CHANGES-1.30).
# The Lead approved this exemption on #91.
# nginx-unprivileged runs as a non-root user and listens on 8080; its pid and temp files live in /tmp.
FROM nginx/nginx-unprivileged:1.30.6-alpine3.24@sha256:2daef144b574804198caccc4041819fa1801ecd5df2252a39646bfa2b1ff3bea
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# A config error fails the build, so CI's image build checks nginx.conf too.
RUN nginx -t
EXPOSE 8080
