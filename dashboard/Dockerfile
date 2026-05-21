FROM node:20-alpine AS builder

WORKDIR /app/dashboard

# Copy dependency definitions and install cleanly
COPY package*.json ./
RUN npm ci || npm install

# Copy remaining Next.js source code
COPY . .

# Disable telemetry and build the production bundle
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- Runner Stage ---
FROM node:20-alpine AS runner

WORKDIR /app/dashboard

ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Copy build artifacts and dependencies from builder stage
COPY --from=builder /app/dashboard/package*.json ./
COPY --from=builder /app/dashboard/node_modules ./node_modules
COPY --from=builder /app/dashboard/.next ./.next
COPY --from=builder /app/dashboard/public ./public
COPY --from=builder /app/dashboard/src ./src

EXPOSE 3000

# Start production server
CMD ["npm", "run", "start"]
