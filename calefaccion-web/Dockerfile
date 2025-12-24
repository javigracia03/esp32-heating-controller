FROM node:18-alpine AS build

WORKDIR /app

# accept VITE_API_BASE as a build-arg and export it so Vite can read it at build time
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Use a custom nginx config to enable SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
