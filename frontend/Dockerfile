FROM node:18-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install
COPY frontend/. .
RUN yarn build

FROM nginx:stable-alpine
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
