import { resolve } from 'path';

export default {
  testEnvironment: 'node',
  roots: [resolve(__dirname, '../../tests/typescript')],
  testMatch: ['**/*.test.ts'],
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { tsconfig: resolve(__dirname, 'tsconfig.json') }],
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  moduleDirectories: ['node_modules', resolve(__dirname, 'node_modules')],
};
