FROM node:0.12

RUN mkdir -p /code

WORKDIR /code

COPY package.json ./

ENV NODE_ENV production
RUN npm install

COPY shareServer.js ./

CMD ["node", "./shareServer.js"]