import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      'react/jsx-dev-runtime': path.resolve(__dirname, '../../../frontend/node_modules/react/jsx-dev-runtime.js'),
      'react/jsx-runtime': path.resolve(__dirname, '../../../frontend/node_modules/react/jsx-runtime.js'),
      'react': path.resolve(__dirname, '../../../frontend/node_modules/react/index.js'),
      'react-dom': path.resolve(__dirname, '../../../frontend/node_modules/react-dom/index.js'),
      '@testing-library/react': path.resolve(__dirname, '../../../frontend/node_modules/@testing-library/react/dist/index.js'),
    }
  },
  test: {
    environment: 'jsdom',
    include: ['**/*.test.*'],
  }
});
