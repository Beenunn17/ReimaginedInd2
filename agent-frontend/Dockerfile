# Stage 1: Build the React application
FROM node:20-alpine AS build

ARG VITE_API_BASE_URL

WORKDIR /app

# Fail the build if the secret is missing or empty, for future debugging
RUN if [ -z "${VITE_API_BASE_URL}" ]; then echo "Error: VITE_API_BASE_URL is not set. Please check your GitHub repository secrets." && exit 1; fi

# Create the .env.production file that Vite will use for the build
RUN echo "VITE_API_BASE_URL=${VITE_API_BASE_URL}" > .env.production

COPY package*.json ./
RUN npm install
COPY . .

# --- FINAL DEBUGGING STEP ---
# Run the build command with a debug flag to get more detailed error output.
# The extra '--' is necessary to pass the flag to the vite command.
RUN npm run build -- --debug

# Stage 2: Serve the built application with NGINX
FROM nginx:1.25-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

