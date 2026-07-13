// Flat ESLint config covering the TypeScript sources and the Svelte components.
// eslint v9 + typescript-eslint + eslint-plugin-svelte (with svelte-eslint-parser
// delegating <script lang="ts"> to the TS parser).
import js from '@eslint/js'
import ts from 'typescript-eslint'
import svelte from 'eslint-plugin-svelte'
import globals from 'globals'

export default ts.config(
  {
    // Build output and vendored deps are never linted.
    ignores: ['dist/', 'node_modules/'],
  },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...svelte.configs['flat/recommended'],
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
  {
    // Svelte files: parse <script lang="ts"> with the TS parser.
    files: ['**/*.svelte', '**/*.svelte.ts'],
    languageOptions: {
      parserOptions: {
        parser: ts.parser,
      },
    },
  },
  {
    // Test files run under Vitest globals (describe/it/expect/vi).
    files: ['**/*.{test,spec}.{ts,js}', 'src/setupTests.ts'],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
)
