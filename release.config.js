const config = {
    branches: ['main'],
    plugins: [
        '@semantic-release/commit-analyzer',
        '@semantic-release/release-notes-generator',
        ['@semantic-release/github', { assets: [{ path: 'build/jaclang-extension.vsix', label: 'Jaclang Extension (VSIX)' }] }],
    ],
};

module.exports = config;
