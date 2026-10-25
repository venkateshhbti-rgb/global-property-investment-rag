module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } },
  plugins: ['react', 'jsx-a11y'],
  extends: ['eslint:recommended', 'plugin:react/recommended', 'plugin:react/jsx-runtime', 'plugin:jsx-a11y/recommended'],
  settings: { react: { version: 'detect' } },
  rules: { 'react/prop-types': 'off', 'react/no-unescaped-entities': 'off' },
  ignorePatterns: ['dist', 'node_modules'],
}
