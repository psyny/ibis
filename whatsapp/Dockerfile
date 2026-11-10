FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund

COPY src ./src

ENV NODE_ENV=production
ENV DATA_DIR=/data/sessions
# Login data must survive restarts: mount a volume at /data
VOLUME /data

EXPOSE 3001

CMD ["node", "src/server.js"]
