FROM node:20-alpine AS build

ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app
COPY apps/pa-web/package.json apps/pa-web/package-lock.json ./
RUN npm ci
COPY apps/pa-web/index.html apps/pa-web/tsconfig.json apps/pa-web/tsconfig.node.json apps/pa-web/vite.config.ts ./
COPY apps/pa-web/src ./src
RUN npm run build

FROM nginx:1.27-alpine
COPY infra/docker/pa-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
