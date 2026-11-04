FROM node:26-slim
WORKDIR /app
ENV NODE_ENV=production \
    PORT=8080
# Node runs the TypeScript sources directly (type stripping), so there is no build step and no runtime package.
COPY package.json ./
COPY src ./src
COPY reference ./reference
COPY fixtures ./fixtures
COPY test ./test
RUN mkdir -p /data
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||8080)+'/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "src/server.ts"]
