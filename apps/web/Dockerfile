# FoldForge Web — Next.js Studio UI
FROM node:20-bookworm-slim AS builder

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json ./apps/web/
COPY packages ./packages
COPY apps/web ./apps/web

WORKDIR /app/apps/web

ARG NEXT_PUBLIC_API_URL=http://api:8000
ARG NEXT_PUBLIC_FOLDFORGE_API_KEY=
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_FOLDFORGE_API_KEY=${NEXT_PUBLIC_FOLDFORGE_API_KEY}

RUN npm ci
RUN npm run build

FROM node:20-bookworm-slim AS runner

WORKDIR /app/apps/web

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=builder /app/apps/web/package.json ./package.json
COPY --from=builder /app/apps/web/node_modules ./node_modules
COPY --from=builder /app/apps/web/.next ./.next
COPY --from=builder /app/apps/web/public ./public

EXPOSE 3000

CMD ["npm", "start"]
