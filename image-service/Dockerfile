# Dockerfile - Module B4.2 - Nguyen Thanh Do (24IT002)
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY . .
RUN mkdir -p storage/images data

ENV PORT=8002
ENV NODE_ENV=production
ENV HOST_IP=192.168.100.12
ENV BASE_URL=http://192.168.100.12:8002

EXPOSE 8002
CMD ["npm", "start"]
