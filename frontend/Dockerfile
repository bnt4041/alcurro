FROM oven/bun:1-alpine

WORKDIR /app

COPY package.json bun.lockb* ./
RUN bun install

COPY . .

EXPOSE 5174

CMD ["sh", "-c", "bun install && exec bun run dev -- --host 0.0.0.0"]
