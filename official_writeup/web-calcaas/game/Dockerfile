FROM denoland/deno:2.5.3
WORKDIR /app
COPY deno.json deno.lock ./
COPY app.tsx ./
RUN deno cache app.tsx
EXPOSE 8000
CMD ["deno", "run", "--allow-net", "--allow-env", "--allow-read", "app.tsx"]
