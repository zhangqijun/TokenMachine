# Multi-stage build for React frontend
FROM node:20-alpine AS builder

# Set proxy for build
ENV http_proxy=http://10.157.59.75:7890
ENV https_proxy=http://10.157.59.75:7890
ENV HTTP_PROXY=http://10.157.59.75:7890
ENV HTTPS_PROXY=http://10.157.59.75:7890

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
