FROM node:18-alpine AS build

WORKDIR /app

# Documentation:
# - Declares a build-time argument `VITE_API_BASE` with default value "/api".
# - Exports that argument into an environment variable `VITE_API_BASE` so subsequent build steps (e.g., a Vite build) can read it.
# - Override at build time with: docker build --build-arg VITE_API_BASE=/your/path .
# - ARG is available only during image build; ENV persists into the final image and is available at runtime and to later build steps.
# - This pattern ensures Vite (which uses variables prefixed with VITE_) can pick up the value during the Docker build.
# - To change the value at container runtime use: docker run -e VITE_API_BASE=/other ... (or rebuild the image if the value must be baked in).
# - Avoid placing secrets here: values used in build may be embedded in the final image/layers.
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
