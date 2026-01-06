FROM node:20-alpine

WORKDIR /app

# COPY package.json i napravi node_modules tijekom build-a
COPY package*.json ./
RUN npm install --production

# COPY seed.js
COPY seed.js .

# Kada se kontejner pokrene, pokreni seed
CMD ["node", "seed.js"]
