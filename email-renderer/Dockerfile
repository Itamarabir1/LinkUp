FROM node:20-slim AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM base AS builder
RUN npm ci
COPY tsconfig.json .
COPY src ./src
RUN npm run build

FROM base AS production
COPY --from=builder /app/dist ./dist
EXPOSE 3001
CMD ["node", "dist/server.js"]
