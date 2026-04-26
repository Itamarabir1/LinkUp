import { defineConfig } from 'orval'

export default defineConfig({
  linkup: {
    input: './openapi-snapshot.json',
    output: {
      target: './src/api/generated/client.ts',
      schemas: './src/api/generated/types',
      client: 'axios',
      httpClient: 'axios',
      baseUrl: '',
      override: {
        mutator: {
          path: './src/api/client.ts',
          name: 'apiMutator',
        },
      },
    },
  },
})
